# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-docstring

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import re

from ansible.plugins.action.normal import ActionModule as _ActionModule
from ansible.module_utils._text import to_text
from ansible.module_utils.six.moves.urllib.parse import urlsplit
from ansible.module_utils.network.common.config import NetworkConfig

try:
  # pylint: disable=unused-import
  from __main__ import display
except ImportError:
  # pylint: disable=ungrouped-imports
  from ansible.utils.display import Display
  display = Display()


class ActionModule(_ActionModule):

  HSRP_ID_PARAMS = [
    'name',
    'group',
  ]

  HSRP_OPTION_PARAMS = [
    'version',
    'priority',
    'preempt',
    'delay_minimum',
    'delay_reload',
    'delay_sync',
    'vip',
    'secondary',
    'auth_type',
    'auth_string',
    'track',
    'track_decrement',
    'track_shutdown'
  ]

  supported_params = HSRP_ID_PARAMS + HSRP_OPTION_PARAMS

  # 指定がないときはこれらで補正する
  DEFAULT_PARAMS = {
    'version': '1',
    'priority': '100',
    'auth_type': 'text',
    'auth_string': 'cisco',
    'preempt': 'disabled',
    'secondary': []
  }


  @staticmethod
  def force_numeric_string(want, key):
    value = want.get(key)
    if value is not None:
      if not isinstance(value, str):
        value = str(value)
        want[key] = value
      if not value.isnumeric():
        return '{} must be number: {}'.format(key, value)


  @staticmethod
  def search_obj_in_list(want, have_list):
    want_name = want.get('name')
    want_group = want.get('group')
    for have in have_list:
      have_name = have.get('name')
      have_group = have.get('group')
      if want_name == have_name and want_group == have_group:
        return have
    return None


  @staticmethod
  def parse_argument(cfg, arg=None):
    match = re.search(r'{} (.+)$'.format(arg), cfg, re.M)
    if match:
      return match.group(1)


  @staticmethod
  def normalize_name(name):

    intf_map = {
      'E': 'Ethernet',
      'F': 'FastEthernet',
      'G': 'GigabitEthernet',
      'TE': 'TenGigabitEthernet',
      'TU': 'Tunnel',
      'MG': 'Mgmt',
      'L': 'Loopback',
      'P': 'Port-channel',
      'V': 'Vlan',
      'S': 'Serial'
    }

    # nameが省略表記の場合はフルネームに置き換える
    if name:
      match = re.match(r'^(?P<intfname>[A-Za-z-]+)(\s+)?(?P<intfnum>\d+.*)', name)
      if match:
        intfname = match.group('intfname')
        intfnum = match.group('intfnum')

        for k, v in intf_map.items():
          if intfname.upper().startswith(k):
            return '{}{}'.format(v, intfnum)

    return name


  def validate_name(self, want):
    name = want.get('name')
    if not name:
      return 'name is needed but not set.'

    if name.startswith('Loop'):
      return 'loopback interface does not support hsrp.'


  def validate_group(self, want):
    if want.get('state') == 'unconfigured':
      return
    key = 'group'
    value = want.get(key)
    if not value:
      return 'hsrp group number is needed but not set.'
    if isinstance(value, int):
      value = str(value)
      want[key] = value
    if not value.isnumeric():
      return 'hsrp group number must be number: {}'.format(value)


  def validate_version(self, want):
    key = 'version'
    value = want.get(key)
    if value:
      if isinstance(value, int):
        value = str(value)
        want[key] = value
      if value not in ['1', '2']:
        return 'hsrp version number must be ["1", "2"]: {}'.format(value)


  def validate_auth_type(self, want):
    key = 'auth_type'
    value = want.get(key)
    if value:
      if not isinstance(value, str):
        value = str(value)
        want[key] = value
      if value not in ['text', 'md5']:
        return 'auth_type must be choice of ["text", "md5"]: {}'.format(value)


  def validate_auth_string(self, want):
    key = 'auth_string'
    value = want.get(key)
    if value:
      if not isinstance(value, str):
        value = str(value)
        want[key] = value
      if want.get('auth_type') == 'text' and len(value) > 8:
        return 'maximum text authentication string length is 8: {}'.format(value)


  def validate_preempt(self, want):
    key = 'preempt'
    value = want.get(key)
    if value:
      if isinstance(value, bool):
        if value:
          value = 'enabled'
        else:
          value = 'disabled'
        want[key] = value
      if value not in ['enabled', 'disabled']:
        return 'preempt must be choice of ["enabled", "disabled"]: {}'.format(value)


  def validate_secondary(self, want):
    key = 'secondary'
    value = want.get(key)
    if value:
      if not isinstance(value, list):
        value = [value]
        want[key] = value


  def validate_priority(self, want):
    key = 'priority'
    value = want.get(key)
    if value:
      if isinstance(value, int):
        value = str(value)
        want[key] = value


  def validate_delay_minimum(self, want):
    return self.force_numeric_string(want, 'delay_minimum')


  def validate_delay_reload(self, want):
    return self.force_numeric_string(want, 'delay_reload')


  def validate_delay_sync(self, want):
    return self.force_numeric_string(want, 'delay_sync')


  def validate_track(self, want):
    return self.force_numeric_string(want, 'track')


  def validate_track_decrement(self, want):
    return self.force_numeric_string(want, 'track_decrement')


  def validate(self, want_list):
    for want in want_list:

      # nameが省略表記されていても大丈夫なように正規化する
      name = want.get('name')
      norm_name = self.normalize_name(name)
      if norm_name != name:
        want['name_input'] = name
        want['name'] = norm_name

      for key in want.keys():
        # to avoid pylint E1102
        # validator = getattr(self, 'validate_{}'.format(key), None)
        validator = getattr(self, 'validate_%s' % key, None)
        if callable(validator):
          msg = validator(want)
          if msg:
            return msg


  def standby_group_config_to_obj(self, group_config_list):

    # "__group_config_list__": [
    #     "ip 3.3.3.1",
    #     "ip 3.3.3.254 secondary",
    #     "preempt delay reload 180",
    #     "authentication cisco2",
    #     "track 1 decrement 10",
    # ],

    obj = {}

    group_config = '\n'.join(group_config_list)

    # vip
    m = re.search(r'ip\s+(\d+\.\d+\.\d+\.\d+)\s*$', group_config, re.M)
    if m:
      obj['vip'] = m.group(1)
    else:
      obj['vip'] = None

    # secondary vip
    m = re.findall(r'ip\s+(\d+\.\d+\.\d+\.\d+)\s+secondary\s*$', group_config, re.M)
    if m:
      obj['secondary'] = m
    else:
      obj['secondary'] = None  # []にする？

    # priority
    m = re.search(r'priority\s+(\d+)\s*$', group_config, re.M)
    if m:
      obj['priority'] = m.group(1)
    else:
      obj['priority'] = None  # 100にする？

    # authentication md5 key-string
    md5_key_string = self.parse_argument(group_config, 'authentication md5 key-string')
    obj['auth_type'] = 'md5' if md5_key_string else 'text'

    if md5_key_string:
      auth_string = md5_key_string
    else:
      auth_string = self.parse_argument(group_config, 'authentication')
    obj['auth_string'] = auth_string

    # preempt
    # preempt delay minimum 60 reload 180 sync 60
    PREEMPT_DELAY = r'''
      ^delay
      (?:\s+(?:minimum\s+(?P<delay_minimum>\d+)))?
      (?:\s+(?:reload\s+(?P<delay_reload>\d+)))?
      (?:\s+(?:sync\s+(?P<delay_sync>\d+)))?
    '''
    m = re.search(r'^preempt', group_config, re.M)
    if m:
      obj['preempt'] = 'enabled'
      preempt_config = self.parse_argument(group_config, 'preempt')
      if preempt_config:
        m = re.search(PREEMPT_DELAY, preempt_config, re.VERBOSE)
        if m:
          obj['delay_minimum'] = m.group('delay_minimum')
          obj['delay_reload'] = m.group('delay_reload')
          obj['delay_sync'] = m.group('delay_sync')
    else:
      obj['preempt'] = 'disabled'
      obj['delay_minimum'] = None
      obj['delay_reload'] = None
      obj['delay_sync'] = None

    # track 1
    # track 1 decrement 10
    # track 1 shutdown
    TRACK = r'''
      ^track\s+(?P<track>\d+)
      (?:\s+(?:decrement\s+(?P<decrement>\d+)))?
      (?:\s+(?P<shutdown>shutdown))?
    '''
    track_config = self.parse_argument(group_config, 'track')
    if track_config:
      m = re.search(TRACK, 'track {}'.format(track_config), re.VERBOSE)
      if m:
        obj['track'] = m.group('track')
        obj['track_decrement'] = m.group('decrement')
        obj['track_shutdown'] = bool(m.group('shutdown'))
    else:
      obj['track'] = None
      obj['track_decrement'] = None
      obj['track_shutdown'] = None

    if self._task.args.get('debug'):
      obj['__group_config_list__'] = group_config_list

    return obj


  def standby_config_to_obj(self, intf_name, standby_config_list):
    results = []

    cfg = '\n'.join(standby_config_list)

    # 先頭のstandbyが取れた状態
    # version 2
    # 1 ip 3.3.3.1
    # 1 preempt
    # 1 track 1

    # HSRPバージョンはインタフェース内で共通
    version = self.parse_argument(cfg, 'version')

    # HSRPグループはインタフェース内に複数存在する可能性があるので、グループごとに分離する
    # 行頭の数字がグループ番号
    match = re.findall(r'^(\d+)\s+\S+', cfg, re.M)
    if match:
      group_list = list(set(match))
      for group in group_list:
        match = re.findall(r'^{}\s+(.+)'.format(group), cfg, re.M)
        if match:
          obj = self.standby_group_config_to_obj(match)

          # インタフェース共通のパラメータを追加
          obj['state'] = 'present'
          obj['name'] = intf_name
          obj['version'] = version
          obj['group'] = group

          results.append(obj)

    return results


  def map_config_to_obj(self, config):
    results = []

    configobj = NetworkConfig(indent=1, contents=config)

    # インタフェース名の一覧を取り出す
    match = re.findall(r'^interface (\S+)', config, re.M)
    if not match:
      return list()

    for intf_name in set(match):
      # インタフェース内にstandbyで始まる設定があるか確認する
      parent = 'interface {}'.format(intf_name)
      cfg = configobj[parent]
      cfg = '\n'.join(cfg.children)
      match = re.findall(r'^standby\s+(.+)', cfg, re.M)
      if not match:
        continue

      # standbyで始まるコンフィグコマンドのリストを渡してオブジェクトに変換する
      standby_config_list = list(match)
      objs = self.standby_config_to_obj(intf_name, standby_config_list)
      if objs:
        results.extend(objs)

    return results


  def args_to_obj(self, args):
    obj = {}

    for p in self.supported_params:
      # そのパラメータが入力したYAMLにある場合だけwantに取り込む
      if p in args:
        obj[p] = args.get(p)

    # stateは設定されていない場合 'present' の扱いにする
    obj['state'] = args.get('state', 'present')

    return obj


  def map_params_to_obj(self):

    results = []

    # パラメータ一覧を渡された場合
    interfaces = self._task.args.get('interfaces')
    if interfaces and isinstance(interfaces, list):
      for item in interfaces:
        obj = self.args_to_obj(item)
        results.append(obj)
      return results

    # パラメータだけが指定された場合
    obj = self.args_to_obj(self._task.args)
    results.append(obj)

    return results


  def to_commands_absent(self, want, have):
    commands = []

    intf_name = want.get('name')
    group = want.get('group')

    if have:
      commands.append('interface {}'.format(intf_name))
      commands.append('no standby {}'.format(group))
      commands.append('exit')

    return commands


  def equals_to(self, want, have):
    if not have:
      return False

    for p in self.HSRP_OPTION_PARAMS:
      want_value = want.get(p)
      want_value = self.DEFAULT_PARAMS.get(p) if want_value is None else want_value
      # listは直接の比較ができないのでsetにする
      if isinstance(want_value, list):
        want_value = set(want_value)

      have_value = have.get(p)
      have_value = self.DEFAULT_PARAMS.get(p) if have_value is None else have_value
      if isinstance(have_value, list):
        have_value = set(have_value)

      if want_value != have_value:
        return False

    return True

  #
  # メモ
  # present_XXX(want, have)
  # HSRPグループを新規作成する場合もあるのでhaveはNoneの場合もある
  # wantの中にXXXキーは必ず存在する
  #

  def present_version(self, want, have):
    commands = []
    key = 'version'

    want_version = want.get(key)

    # create new
    if not have:
      if want_version and want_version != self.DEFAULT_PARAMS.get(key):
        commands.append('standby version {}'.format(want_version))
      return commands

    # modify
    want_version = self.DEFAULT_PARAMS.get(key) if want_version is None else want_version

    have_version = have.get(key)
    have_version = self.DEFAULT_PARAMS.get(key) if have_version is None else have_version

    if want_version != have_version:
      # HSRPのバージョンを変える
      commands.append('standby version {}'.format(want_version))

    return commands


  def present_vip(self, want, have):
    commands = []
    group = want.get('group')
    key = 'vip'

    want_vip = want.get(key)

    # create new
    if not have:
      if want_vip:
        commands.append('standby {} ip {}'.format(group, want_vip))
      return commands

    # modify
    have_vip = have.get(key)

    if want_vip != have_vip:
      if want_vip:
        commands.append('standby {} ip {}'.format(group, want_vip))
      else:
        commands.append('no standby {} ip {}'.format(group, have_vip))

    return commands


  def present_secondary(self, want, have):
    commands = []
    group = want.get('group')

    want_secondary = want.get('secondary')

    # create new
    if not have:
      if want_secondary:
        for item in want_secondary:
          commands.append('standby {} ip {} secondary'.format(group, item))
      return commands

    # modify
    want_secondary = [] if want_secondary is None else want_secondary

    have_secondary = have.get('secondary')
    have_secondary = [] if have_secondary is None else have_secondary

    if set(want_secondary) != set(have_secondary):

      missings = set(want_secondary).difference(set(have_secondary))
      for m in missings:
        commands.append('standby {} ip {} secondary'.format(group, m))

      superfluous = set(have_secondary).difference(set(want_secondary))
      for m in superfluous:
        commands.append('no standby {} ip {} secondary'.format(group, m))

    return commands


  def present_preempt(self, want, have):
    commands = []
    group = want.get('group')
    key = 'preempt'

    want_preempt = want.get(key)
    want_delay_minimum = want.get('delay_minimum')
    want_delay_reload = want.get('delay_reload')
    want_delay_sync = want.get('delay_sync')

    # create new
    if not have:

      if want_preempt and want_preempt != self.DEFAULT_PARAMS.get(key):
        cmd = 'standby {} preempt'.format(group)
        if any([want_delay_minimum, want_delay_reload, want_delay_sync]):
          cmd += ' delay '
          if want_delay_minimum:
            cmd += 'minimum {} '.format(want_delay_minimum)
          if want_delay_reload:
            cmd += 'reload {} '.format(want_delay_reload)
          if want_delay_sync:
            cmd += 'sync {}'.format(want_delay_sync)
          cmd = cmd.strip()
        commands.append(cmd)

      return commands

    # modify
    want_preempt = self.DEFAULT_PARAMS.get(key) if want_preempt is None else want_preempt

    have_preempt = have.get(key)
    have_delay_minimum = have.get('delay_minimum')
    have_delay_reload = have.get('delay_reload')
    have_delay_sync = have.get('delay_sync')

    if want_preempt != have_preempt:
      # preempt設定の有無そのものを変更する
      if want_preempt == 'enabled':
        # 既存がdisabledなので有効にする
        cmd = 'standby {} preempt'.format(group)
        if any([want_delay_minimum, want_delay_reload, want_delay_sync]):
          cmd += ' delay '
          if want_delay_minimum:
            cmd += 'minimum {} '.format(want_delay_minimum)
          if want_delay_reload:
            cmd += 'reload {} '.format(want_delay_reload)
          if want_delay_sync:
            cmd += 'sync {}'.format(want_delay_sync)
          cmd = cmd.strip()
        commands.append(cmd)
      else:
        # 既存がenabledなので無効にする
        commands.append('no standby {} preempt'.format(group))
    elif want_delay_minimum != have_delay_minimum or want_delay_reload != have_delay_reload or want_delay_sync != have_delay_sync:
      # preempt自体は一致しているものの、細かいパラメータを変更する場合
      # 一度noでdelayだけ削除する
      commands.append('no standby {} preempt delay'.format(group))
      cmd = 'standby {} preempt'.format(group)
      if any([want_delay_minimum, want_delay_reload, want_delay_sync]):
        cmd += ' delay '
        if want_delay_minimum:
          cmd += 'minimum {} '.format(want_delay_minimum)
        if want_delay_reload:
          cmd += 'reload {} '.format(want_delay_reload)
        if want_delay_sync:
          cmd += 'sync {}'.format(want_delay_sync)
        cmd = cmd.strip()
      commands.append(cmd)

    return commands


  def present_auth(self, want, have):
    commands = []
    group = want.get('group')

    want_auth_type = want.get('auth_type')
    want_auth_string = want.get('auth_string')

    # create new
    if not have:
      if want_auth_string:
        if want_auth_type == self.DEFAULT_PARAMS.get('auth_type'):
          if want_auth_string != self.DEFAULT_PARAMS.get('auth_string'):
            commands.append('standby {} authentication text {}'.format(group, want_auth_string))
        else:
          commands.append('standby {} authentication {} key-string {}'.format(group, want_auth_type, want_auth_string))

      return commands

    # modify
    want_auth_type = self.DEFAULT_PARAMS.get('auth_type') if want_auth_type is None else want_auth_type
    have_auth_type = have.get('auth_type')

    if want_auth_type == 'text' and have_auth_type is None:
      want_auth_string = self.DEFAULT_PARAMS.get('auth_string')

    have_auth_string = have.get('auth_string')
    if have_auth_type == 'text' and have_auth_string is None:
      have_auth_string = self.DEFAULT_PARAMS.get('auth_string')

    if want_auth_type != have_auth_type or want_auth_string != have_auth_string:
      # 一度削除して追加する
      commands.append('no standby {} authentication'.format(group))
      if want_auth_string:
        if want_auth_type == 'text':
          if want_auth_string != self.DEFAULT_PARAMS.get('auth_string'):
            commands.append('standby {} authentication text {}'.format(group, want_auth_string))
        else:
          commands.append('standby {} authentication md5 key-string {}'.format(group, want_auth_string))

    return commands


  def present_priority(self, want, have):
    commands = []
    group = want.get('group')

    want_priority = want.get('priority')

    # create new
    if not have:
      if want_priority and want_priority != self.DEFAULT_PARAMS.get('priority'):
        commands.append('standby {} priority {}'.format(group, want_priority))
      return commands

    # modify
    want_priority = self.DEFAULT_PARAMS.get('priority') if want_priority is None else want_priority

    have_priority = have.get('priority')
    have_priority = self.DEFAULT_PARAMS.get('priority') if have_priority is None else have_priority

    if want_priority != have_priority:
      if want_priority:
        commands.append('standby {} priority {}'.format(group, want_priority))
      else:
        commands.append('no standby {} priority'.format(group))

    return commands


  def present_track(self, want, have):
    commands = []
    group = want.get('group')

    want_track = want.get('track')
    want_track_decrement = want.get('track_decrement')

    # haveのtrack_shutdownはboolなので、型を一致させる
    want_track_shutdown = want.get('track_shutdown')
    want_track_shutdown = False if want_track_shutdown is None else want_track_shutdown

    # create new
    if not have:
      if want_track:
        cmd = 'standby {} track {}'.format(group, want_track)
        if want_track_decrement:
          cmd += ' decrement {}'.format(want_track_decrement)
        elif want_track_shutdown is True:
          cmd += ' shutdown'
        commands.append(cmd)

      return commands

    # modify
    have_track = have.get('track')
    have_track_decrement = have.get('track_decrement')
    have_track_shutdown = have.get('track_shutdown')

    if want_track is None and have_track is None:
      pass
    elif want_track is None and have_track is not None:
      # 消す
      commands.append('no standby {} track {}'.format(group, have_track))
    elif want_track is not None and have_track is None:
      # 追加
      cmd = 'standby {} track {}'.format(group, want_track)
      track_decrement = want.get('track_decrement')
      track_shutdown = want.get('shutdown')
      if track_decrement:
        cmd += ' decrement {}'.format(track_decrement)
      elif track_shutdown is True:
        cmd += ' shutdown'
      commands.append(cmd)
    elif want_track is not None and have_track is not None:
      # 何か一個でも違っているなら一度消して作り直す
      if want_track != have_track or want_track_decrement != have_track_decrement or want_track_shutdown != have_track_shutdown:
        commands.append('no standby {} track {}'.format(group, have_track))
        cmd = 'standby {} track {}'.format(group, want_track)
        track_decrement = want.get('track_decrement')
        track_shutdown = want.get('shutdown')
        if track_decrement:
          cmd += ' decrement {}'.format(track_decrement)
        elif track_shutdown is True:
          cmd += ' shutdown'
        commands.append(cmd)

    return commands


  def to_commands_present(self, want, have):
    commands = []

    # 完全に一致するなら何もしなくていい
    if self.equals_to(want, have):
      return commands

    intf_name = want.get('name')
    interface = 'interface {}'.format(intf_name)
    commands.append(interface)

    # これらパラメータに関して関数 present_XXX(want, have) を呼び出す
    params = [
      'version',
      'vip',
      'secondary',
      'preempt',
      'auth',
      'priority',
      'track'
    ]

    for p in params:
      # wantにキーがある場合、すなわちYAMLでパラメータが書かれているときだけ
      if p in want:
        func = getattr(self, 'present_%s' % p, None)
        if callable(func):
          cmds = func(want, have)
          if cmds:
            commands.extend(cmds)

    if commands:
      if commands[-1] == interface:
        commands.pop(-1)
      else:
        commands.append('exit')

    return commands


  def to_commands(self, want, have_list):
    commands = []

    # nameとgroupが一致するものを探す
    # 存在しなければhaveはNoneになる
    have = self.search_obj_in_list(want, have_list)

    state = want.get('state')

    if state == 'absent':
      # 削除する対象があるときだけ実行する
      if have:
        cmds = self.to_commands_absent(want, have)
        if cmds:
          commands.extend(cmds)

    if state == 'present':
      # これからHSRPグループを作成する場合もあるので、haveがNoneの場合も実行する
      cmds = self.to_commands_present(want, have)
      if cmds:
        commands.extend(cmds)

    return commands


  def to_commands_list(self, want_list, have_list):
    commands = []

    for want in want_list:
      cmds = self.to_commands(want, have_list)
      if cmds:
        commands.extend(cmds)

    return commands


  def _handle_template(self, key_path):
    # pylint: disable=W0212
    if not self._task.args.get(key_path):
      return

    src = self._task.args.get(key_path)

    working_path = self._loader.get_basedir()
    if self._task._role is not None:
      working_path = self._task._role._role_path

    if os.path.isabs(src) or urlsplit('src').scheme:
      source = src
    else:
      source = self._loader.path_dwim_relative(working_path, 'templates', src)
      if not source:
        source = self._loader.path_dwim_relative(working_path, src)

    if not os.path.exists(source):
      raise ValueError('path specified in src not found')

    try:
      with open(source, 'r') as f:
        template_data = to_text(f.read())
    except IOError:
      return dict(failed=True, msg='unable to load file, {}'.format(src))

    # Create a template search path in the following order:
    # [working_path, self_role_path, dependent_role_paths, dirname(source)]
    searchpath = [working_path]
    if self._task._role is not None:
      searchpath.append(self._task._role._role_path)
      if hasattr(self._task, "_block:"):
        dep_chain = self._task._block.get_dep_chain()
        if dep_chain is not None:
          for role in dep_chain:
            searchpath.append(role._role_path)
    searchpath.append(os.path.dirname(source))
    self._templar.environment.loader.searchpath = searchpath
    self._task.args[key_path] = self._templar.template(template_data)


  def run(self, tmp=None, task_vars=None):
    del tmp  # tmp no longer has any effect

    # ファイルへのパスを指定されていたらファイルの中身に展開する
    try:
      self._handle_template('running_config_path')
    except ValueError as e:
      return dict(failed=True, msg=to_text(e))

    # モジュールを実行する
    # ただし、このモジュールは何もしない
    result = super(ActionModule, self).run(task_vars=task_vars)

    #
    # モジュール実行後の後工程処理
    #

    if self._task.args.get('running_config_path'):
      config = self._task.args.get('running_config_path')
    else:
      config = self._task.args.get('running_config')

    have_list = self.map_config_to_obj(config)
    if self._task.args.get('debug'):
      result['have'] = have_list

    want_list = self.map_params_to_obj()
    if self._task.args.get('debug'):
      result['want'] = want_list

    msg = self.validate(want_list)
    if msg:
      result['failed'] = True
      result['msg'] = msg
      return result

    commands = self.to_commands_list(want_list, have_list)
    result['commands'] = commands

    return result
