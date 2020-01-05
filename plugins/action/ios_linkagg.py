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

  supported_params = ('group', 'mode', 'members')


  @staticmethod
  def search_obj_in_list(want, have_list):
    want_group = want.get('group')
    for have in have_list:
      if have.get('group') == want_group:
        return have
    return None


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


  def validate_mode(self, want):
    key = 'mode'
    mode = want.get(key)
    if mode is None:
      return 'mode is needed but not set.'

    # yaml parser decode 'on' as True
    if isinstance(mode, bool) and mode is True:
      mode = 'on'
      want[key] = mode
    if mode not in ['active', 'on', 'passive', 'auto', 'desirable']:
      return "mode must be choice of ['active', 'on', 'passive', 'auto', 'desirable']."


  def validate_group(self, want):
    key = 'group'
    group = want.get(key)
    if group is None:
      return 'channel group number is needed but not set.'

    if isinstance(group, int):
      group = str(group)
      want[key] = group
    if not group.isnumeric():
      return 'channel group number must be number: {}'.format(group)


  def validate_members(self, want):
    key = 'members'
    members = want.get(key)
    if members and isinstance(members, str):
      members = [members]
      want[key] = members

    for i, name in enumerate(members):
      norm_name = self.normalize_name(name)
      if norm_name != name:
        members[i] = norm_name


  def validate(self, want_list):
    for want in want_list:

      # presentのときのみ検証する
      state = want.get('state')
      if state != 'present':
        continue

      # 存在するキーについてのみvaludate_key()を実行する
      for key in want.keys():
        # to avoid pylint E1102
        # validator = getattr(self, 'validate_{}'.format(key), None)
        validator = getattr(self, 'validate_%s' % key, None)
        if callable(validator):
          msg = validator(want)
          if msg:
            return msg


  def equals_to(self, want, have):
    for key in ['group', 'mode']:
      if want.get(key) != have.get(key):
        return False

    if set(want.get('members')) != set(have.get('members')):
      return False

    return True


  def map_config_to_obj(self, config):

    configobj = NetworkConfig(indent=1, contents=config)

    # interface port-channel xxx を探す
    match = re.findall(r'^interface Port-channel(\S+)', config, re.M)
    if not match:
      return list()

    results = []
    for po_number in set(match):
      obj = {}
      obj['state'] = 'present'
      obj['group'] = po_number

      # channel-group xxx を設定しているインタフェースを捕まえる
      members = []
      mode = None
      match = re.findall(r'^interface (\S+)', config, re.M)
      if match:
        for intf_name in set(match):
          cfg = configobj['interface {}'.format(intf_name)]
          cfg = '\n'.join(cfg.children)
          m = re.search(r'^channel-group {} mode (\S+)'.format(po_number), cfg, re.M)
          if m:
            members.append(intf_name)
            mode = m.group(1)

      obj['mode'] = mode
      obj['members'] = members

      results.append(obj)

    return results


  def args_to_obj(self, args):
    obj = {}

    for p in self.supported_params:
      # そのパラメータが入力したYAMLにある場合だけwantに取り込む
      if p in args:
        obj[p] = args.get(p)

    # stateは設定されていない場合'present'の扱いにする
    obj['state'] = args.get('state', 'present')

    return obj


  def map_params_to_obj(self):
    results = []

    # パラメータ一覧を渡された場合
    port_channels = self._task.args.get('port_channels')
    if port_channels and isinstance(port_channels, list):
      for item in port_channels:
        obj = self.args_to_obj(item)
        results.append(obj)
      return results

    # aggregateで一覧を渡された場合
    aggregate = self._task.args.get('aggregate')
    if aggregate and isinstance(aggregate, list):
      for item in aggregate:
        # _task.argsを使ってオブジェクトを作成してからaggregateの内容を追記する
        obj = self.args_to_obj(self._task.args)
        obj.update(item)
        results.append(obj)
      return results

    # パラメータだけが指定された場合
    obj = self.args_to_obj(self._task.args)
    results.append(obj)

    return results


  # メモ
  # to_commands_absent(want, have)
  # haveがNoneになることはない

  def to_commands_absent(self, want, have):
    # absentを指定された場合
    # 既存設定に存在するなら、そのPort-Channelをnoで削除する
    # 物理足のchannle-groupも自動で消える
    if have:
      group = want.get('group')
      cmds = [
        'no interface port-channel {}'.format(group)
      ]
      return cmds

  # メモ
  # to_commands_present(want, have)
  # 新規作成も考えられるのでhaveがNoneの場合もある

  def to_commands_present(self, want, have):
    group = want.get('group')
    mode = want.get('mode')
    want_members = want.get('members', [])

    commands = []

    #
    # 同じチャネルグループが未作成なら、新規で作成する
    #
    if not have:
      cmds = [
        'interface port-channel {}'.format(group),
        'exit'
      ]
      commands.extend(cmds)
      for m in want_members:
        cmds = [
          'interface {0}'.format(m),
          'channel-group {} mode {}'.format(group, mode),
          'exit'
        ]
        commands.extend(cmds)
      return commands

    # 以下、haveは存在する

    #
    # 完全に一致するなら何もしなくていい
    #
    if self.equals_to(want, have):
      return commands

    # 以下、haveは存在し、wantとhaveは一致していない

    have_members = have.get('members')
    have_mode = have.get('mode')

    #
    # port-channelは作成済みで、物理足におけるchannel-groupが存在しない場合
    # 物理足に設定を追加する
    #
    if not have_members:
      for m in want_members:
        cmds = [
          'interface {}'.format(m),
          'channel-group {} mode {}'.format(group, mode),
          'exit'
        ]
        commands.extend(cmds)
      return commands

    # 以下、既存にport-channelが存在し、メンバーも存在する

    #
    # modeの変更を指示されてしまった場合は、一度全部のメンバーを削除してその後新規で作り直さなければならない
    #
    if mode != have_mode:
      for m in have_members:
        cmds = [
          'interface {}'.format(m),
          'no channel-group',
          'exit'
        ]
        commands.extend(cmds)
      for m in want_members:
        cmds = [
          'interface {}'.format(m),
          'channel-group {} mode {}'.format(group, mode),
          'exit'
        ]
        commands.extend(cmds)
      return commands

    # 以下、既存にport-channelが存在し、メンバーも存在し、モードの変更もない

    if set(want_members) != set(have_members):
      missing_members = set(want_members).difference(set(have_members))
      for m in missing_members:
        cmds = [
          'interface {}'.format(m),
          'channel-group {} mode {}'.format(group, mode),
          'exit'
        ]
        commands.extend(cmds)

      superfluous_members = set(have_members).difference(set(want_members))
      for m in superfluous_members:
        cmds = [
          'interface {}'.format(m),
          'no channel-group',
          'exit'
        ]
        commands.extend(cmds)

    return commands


  def to_commands(self, want, have_list):

    commands = []

    state = want.get('state')
    have = self.search_obj_in_list(want, have_list)

    if state == 'absent':
      # haveが存在するときのみ実行
      if have:
        cmds = self.to_commands_absent(want, have)
        if cmds:
          commands.extend(cmds)

    if state == 'present':
      # 新規で作成することもあるのでhaveがNoneの場合も実行
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

    commands = self.to_commands_list(want_list=want_list, have_list=have_list)

    result['commands'] = commands
    return result
