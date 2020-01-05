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

  supported_params = ('mode', 'access_vlan', 'native_vlan', 'trunk_vlans', 'nonegotiate')


  @staticmethod
  def get_value(want, key, none_is='', converter=str):
    if want is None:
      return None

    # キーがなければNone
    if key not in want:
      return None

    # キーはあるものの値がない場合は空白文字''を返却
    if want.get(key) is None:
      return none_is

    # デフォルトではstrに変換
    if converter:
      return converter(want.get(key))

    return want.get(key)


  @staticmethod
  def search_obj_in_list(name, lst):
    for o in lst:
      if o['name'] == name:
        return o
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


  @staticmethod
  def vlan_str_to_list(vlan_str):
    if vlan_str is None:
      return None

    # ensure vlan_str is string type
    if not isinstance(vlan_str, str):
      vlan_str = str(vlan_str)

    # convert 'ALL' to 1-4094
    if vlan_str.lower() == 'all':
      vlan_str = '1-4094'

    result = []
    if vlan_str:
      for part in vlan_str.split(','):
        if part.lower() == 'none':
          break
        if '-' in part:
          start, stop = (int(i) for i in part.split('-'))
          result.extend(range(start, stop + 1))
        else:
          result.append(int(part))

    return sorted(result)


  @staticmethod
  def vlan_list_to_str(vlan_list):
    vlan_list = sorted(vlan_list)
    results = []
    start = None
    stop = None

    for item in vlan_list:
      if not start:
        start = item
      else:
        if not stop:
          if item == start + 1:
            stop = item
          else:
            results.append(str(start))
            start = item
        else:
          if item == stop + 1:
            stop = item
          else:
            results.append(str(start) + '-' + str(stop))
            start = item
            stop = None

    if start and stop:
      results.append(str(start) + '-' + str(stop))
    elif start:
      results.append(str(start))

    return ','.join(results)


  @staticmethod
  def parse_config_argument(configobj, name, arg=None):

    # nameで指定したインタフェース配下のコンフィグを取り出す
    parent = 'interface {}'.format(name)
    cfg = configobj[parent]
    cfg = '\n'.join(cfg.children)

    # 正規表現argに一致し、その後ろに続く文字列を返す
    match = re.search(r'{} (.+)$'.format(arg), cfg, re.M)
    if match:
      return match.group(1)


  @staticmethod
  def parse_config_argument_all(configobj, name, arg=None):

    # nameで指定したインタフェース配下のコンフィグを取り出す
    parent = 'interface {}'.format(name)
    cfg = configobj[parent]
    cfg = '\n'.join(cfg.children)

    values = []
    matches = re.finditer(r'{} (.+)$'.format(arg), cfg, re.M)
    for match in matches:
      match_str = match.group(1).strip()
      values.append(match_str)

    return values


  @staticmethod
  def map_show_vlan_to_obj(show_vlan):
    vlans = set()
    lines = show_vlan.splitlines()
    for line in lines:
      match = re.search(r'^(\d+)\s', line)
      if match:
        # vlan id is stored as int
        vlans.add(int(match.group(1)))

    return sorted(list(vlans))


  @staticmethod
  def parse_show_interfaces_switchport(show_interfaces_switchport):
    # インタフェースごとに分割したリストを返す

    if not show_interfaces_switchport:
      return []

    results = []
    sections = []
    lines = show_interfaces_switchport.splitlines()
    for line in lines:
      if line.strip() == '':
        continue

      match = re.search(r'^Name:', line)
      if match:
        if sections:
          section = '\n'.join(sections)
          results.append(section)
          sections = []
      sections.append(line)

    if sections:
      section = '\n'.join(sections)
      results.append(section)

    return results


  def map_show_interfaces_switchport_to_obj(self, show_interfaces_switchport):
    if not show_interfaces_switchport:
      return list()

    results = []

    sections = self.parse_show_interfaces_switchport(show_interfaces_switchport)
    for section in sections:

      # show interface switchportの出力ではインタフェース名が省略語になっているので変換する
      # Gi0/1 -> GigabitEthernet0/1
      m = re.search(r'Name: (.*)$', section, re.M)
      if m:
        name = m.group(1)
        name = self.normalize_name(name)
      else:
        continue

      m = re.search(r'Administrative Mode: (?:.* )?(\w+)$', section, re.M)
      if m:
        mode = m.group(1)

      m = re.search(r'Switchport: (\S+)$', section, re.M)
      if m:
        switchport = m.group(1)

      m = re.search(r'Access Mode VLAN: (\d+)', section)
      if m:
        access = m.group(1)

      m = re.search(r'Trunking Native Mode VLAN: (\d+)', section)
      if m:
        native = m.group(1)

      m = re.search(r'Trunking VLANs Enabled: (.+)$', section, re.M)
      if m:
        trunk = m.group(1)

      # negotiationはboolに変換
      m = re.search(r'Negotiation of Trunking: (\S+)$', section, re.M)
      if m:
        negotiation = m.group(1)
        nonegotiate = bool(negotiation == 'Off')

      results.append({
        'name': name,
        'mode': mode,
        'switchport': switchport,
        'nonegotiate': nonegotiate,  # bool
        'access_vlan': access,
        'native_vlan': native,
        'trunk_vlans': trunk
      })

      # {
      #     "access_vlan": "2",
      #     "mode": "access",
      #     "name": "GigabitEthernet0/1",
      #     "native_vlan": "1",
      #     "negotiation": "False",
      #     "switchport": "Enabled",
      #     "trunk_vlans": "1-4094"
      # },

    return results


  def map_config_to_obj(self, config):
    results = []

    # ほとんどの情報はshow interfaces switchportから読み取るので、
    # running-configはチャネルが設定されているかどうか、しか見ない

    match = re.findall(r'^interface (\S+)', config, re.M)

    configobj = NetworkConfig(indent=1, contents=config)

    for item in set(match):
      # 'channel-group'で始まるコマンドのオプションを取り出す。コマンドがなければNone
      channel_group = self.parse_config_argument(configobj, item, 'channel-group')

      obj = {
        'name': item,
        'channel_group': channel_group,
        'state': 'present'
      }
      results.append(obj)

    return results


  def args_to_obj(self, args):
    obj = {}
    for p in self.supported_params:
      # そのパラメータが入力したYAMLにある場合だけwantに取り込む
      if p in args:
        value = args.get(p)
        # 空白スペースはNoneに初期化する
        if isinstance(value, str) and value.strip() == '':
          value = None
        obj[p] = value

    # stateは設定されていない場合'present'の扱いにする
    obj['state'] = args.get('state', 'present')

    return obj


  def map_params_to_obj(self):
    results = []

    # 一覧を渡された場合
    interfaces = self._task.args.get('interfaces')
    if interfaces and isinstance(interfaces, list):
      for item in interfaces:
        obj = self.args_to_obj(item)
        obj['name'] = item.get('name')
        results.append(obj)
      return results

    # aggregateとして複数渡された場合
    aggregate = self._task.args.get('aggregate')
    if aggregate and isinstance(aggregate, list):
      for item in aggregate:
        # インタフェースの数だけパラメータオブジェクトを作成してからaggregateの内容を追記する
        obj = self.args_to_obj(self._task.args)
        obj.update(item)
        results.append(obj)
      return results

    # パラメータだけが指定された場合
    obj = self.args_to_obj(self._task.args)
    obj['name'] = self._task.args.get('name')
    results.append(obj)

    return results


  def to_commands_unconfigured(self, have):
    cmds = []

    all_default = all([
      bool(str(have.get('access_vlan')) == '1'),
      bool(str(have.get('native_vlan')) == '1'),
      bool(str(have.get('trunk_vlans')) == 'ALL'),
      bool(have.get('mode') == 'access' or have.get('mode') == 'auto')
    ])

    if not all_default:
      cmds.append('no switchport trunk encapsulation')
      cmds.append('no switchport nonegotiate')
      cmds.append('no switchport mode')
      cmds.append('no switch access vlan')
      cmds.append('no switchport trunk native vlan')
      cmds.append('no switchport trunk allowed vlan')

    return cmds


  def to_commands_absent(self, want, have):
    cmds = []

    want_mode = want.get('mode')

    # mode
    want_mode = self.get_value(want, 'mode')
    have_mode = self.get_value(have, 'mode')
    if want_mode is None:
      pass
    else:
      # デフォルトのモードはaccessなので、それ以外なら消す
      if have_mode != 'access':
        cmds.append('no switchport mode')

    # access_vlan
    want_access_vlan = self.get_value(want, 'access_vlan')
    have_access_vlan = self.get_value(have, 'access_vlan')
    if want_access_vlan is None:
      pass
    else:
      # 指定されたaccess vlanが存在しない(absentの)状態にする -> デフォルトの状態にする
      if have_access_vlan != '1':
        cmds.append('no switchport access vlan')

    # trunk_vlans
    want_trunk_vlans = self.get_value(want, 'trunk_vlans')
    have_trunk_vlans = self.get_value(have, 'trunk_vlans')
    want_trunk_list = self.vlan_str_to_list(want_trunk_vlans)
    have_trunk_list = self.vlan_str_to_list(have_trunk_vlans)

    # (0) want, have = None, 2-3     --> do nothing
    # (1) want, have = '', 2-3       --> no switchport trunk allowed vlan
    # (2) want, have = 'ALL', 2-3    --> no switchport trunk allowed vlan
    # (3) want, have = 2-3, 2-3      --> no switchport trunk allowed vlan
    # (4) want, have = 2,3, 2,3,4,5  --> switchport trunk allowed vlan remove 2-3

    if want_trunk_vlans is None:
      # (0)
      pass
    elif want_trunk_vlans == '':
      if have_trunk_vlans != 'ALL':
        # (1)
        cmds.append('no switchport trunk allowed vlan')
    elif want_trunk_vlans == 'ALL':
      if have_trunk_vlans != 'ALL':
        # (2)
        cmds.append('no switchport trunk allowed vlan')
    elif want_trunk_vlans == have_trunk_vlans:
      # (3)
      cmds.append('no switchport trunk allowed vlan')
    else:
      # (4)
      vlans_to_del = set(want_trunk_list).intersection(have_trunk_list)
      if vlans_to_del:
        vlans_to_del = self.vlan_list_to_str(vlans_to_del)
        cmd = 'switchport trunk allowed vlan remove {0}'.format(vlans_to_del)
        cmds.append(cmd)

    # no switchport trunk native vlan
    # native vlanをabsentする、すなわちデフォルトに戻す。数字は何を指定しても同じ。
    want_native_vlan = self.get_value(want, 'native_vlan')
    have_native_vlan = self.get_value(have, 'native_vlan')
    if want_native_vlan is None:
      pass
    else:
      if have_native_vlan != '1':
        cmds.append('no switchport trunk native vlan')

    # no switchport nonegotiate
    # absentなので、switchport nonegotiateが設置されていないのが正しい状態
    want_nonegotiate = self.get_value(want, 'nonegotiate', none_is=False, converter=bool)
    have_nonegotiate = self.get_value(have, 'nonegotiate', none_is=False, converter=bool)
    if want_nonegotiate is None:
      pass
    elif want_nonegotiate is True:  # -> Falseにしたい
      if have_nonegotiate is not False:
        cmds.append('no switchport nonegotiate')
    elif want_nonegotiate is False:  # -> Trueにしたい
      if have_nonegotiate is not True:
        cmds.append('switchport nonegotiate')

    return cmds


  def to_commands_present(self, want, have):

    cmds = []

    #
    # キーの値を空にした場合は、デフォルトの状態にしたいものとみなす
    #

    # switchport mode <access, trunk>
    want_mode = self.get_value(want, 'mode')
    have_mode = self.get_value(have, 'mode')

    if want_mode is None:
      pass
    elif want_mode == '':
      if have_mode != 'access':
        cmds.append('no switchport mode')
    elif want_mode == 'access':
      if have_mode != 'access':
        cmds.append('switchport mode access')
    elif want_mode == 'trunk':
      if have_mode != 'trunk':
        cmds.append('switchport trunk encapsulation dot1q')
        cmds.append('switchport mode trunk')

    # switchport access vlan
    want_access_vlan = self.get_value(want, 'access_vlan')
    have_access_vlan = self.get_value(have, 'access_vlan')
    if want_access_vlan is None:
      pass
    elif want_access_vlan == '':
      if have_access_vlan != '1':
        cmds.append('no switchport access vlan')
    elif want_access_vlan != have_access_vlan:
      cmds.append('switchport access vlan {0}'.format(want_access_vlan))

    # switchport trunk allowed vlan
    want_trunk_vlans = self.get_value(want, 'trunk_vlans')
    have_trunk_vlans = self.get_value(have, 'trunk_vlans')
    want_trunk_list = self.vlan_str_to_list(want_trunk_vlans)
    have_trunk_list = self.vlan_str_to_list(have_trunk_vlans)

    # (0) want, have = None, 2-3     --> do nothing
    # (1) want, have = '', 2-3       --> no switchport trunk allowed vlan
    # (2) want, have = 'ALL', 2-3    --> no switchport trunk allowed vlan
    # (3) want, have = 2-3, 'ALL'    --> switchport trunk allowed vlan add 2-3
    # (4) want, have = 2-3, 2        --> add and/or remove

    if want_trunk_vlans is None:
      # (0)
      pass
    elif want_trunk_vlans == '':
      # (1)
      if have_trunk_vlans != 'ALL':
        cmds.append('no switchport trunk allowed vlan')
    elif want_trunk_list != have_trunk_list:
      if want_trunk_vlans == 'ALL':
        # (2)
        cmds.append('no switchport trunk allowed vlan')
      else:
        if have_trunk_vlans == 'ALL':
          # (3)
          cmds.append('switchport trunk allowed vlan {0}'.format(want_trunk_vlans))
        else:
          # (4)
          vlans_to_add = set(want_trunk_list).difference(have_trunk_list)
          if vlans_to_add:
            vlans_to_add = self.vlan_list_to_str(vlans_to_add)
            cmds.append('switchport trunk allowed vlan add {0}'.format(vlans_to_add))
          vlans_to_del = set(have_trunk_list).difference(want_trunk_list)
          if vlans_to_del:
            vlans_to_del = self.vlan_list_to_str(vlans_to_del)
            cmds.append('switchport trunk allowed vlan remove {0}'.format(vlans_to_del))

    # switchport trunk native vlan
    want_native_vlan = self.get_value(want, 'native_vlan')
    have_native_vlan = self.get_value(have, 'native_vlan')
    if want_native_vlan is None:
      pass
    elif want_native_vlan == '':
      if have_native_vlan != '1':
        cmds.append('no switchport trunk native vlan')
    elif want_native_vlan != have_native_vlan:
      cmds.append('switchport trunk native vlan {0}'.format(want_native_vlan))

    # switchport nonegotiate
    want_nonegotiate = self.get_value(want, 'nonegotiate', none_is=False, converter=bool)
    have_nonegotiate = self.get_value(have, 'nonegotiate', none_is=False, converter=bool)
    if want_nonegotiate is None:
      pass
    elif want_nonegotiate is True:  # -> Trueにしたい
      if have_nonegotiate is not True:
        cmds.append('switchport nonegotiate')
    elif want_nonegotiate is False:  # -> Falseにしたい
      if have_nonegotiate is not False:
        cmds.append('no switchport nonegotiate')

    return cmds


  def to_commands(self, want, have):

    commands = []

    intf_name = want.get('name')

    # 'interface GigabitEthernet1'
    interface = 'interface ' + intf_name
    commands.append(interface)

    state = want.get('state')

    if state == 'present':
      cmds = self.to_commands_present(want, have)
      if cmds:
        commands.extend(cmds)

    if state == 'unconfigured':
      cmds = self.to_commands_unconfigured(have)
      if cmds:
        commands.extend(cmds)

    if state == 'absent':
      cmds = self.to_commands_absent(want, have)
      if cmds:
        commands.extend(cmds)

    if commands[-1] == interface:
      commands.pop(-1)

    return commands


  def to_commands_list(self, want_list, have_list):
    commands = []

    for want in want_list:
      name = want.get('name')
      have = self.search_obj_in_list(name, have_list)
      # 対象となるインタフェースが存在するときだけ実行
      if have:
        cmds = self.to_commands(want, have)
        commands.extend(cmds)

    return commands


  @staticmethod
  def validate(want, have, vlan_list):

    # 1-4094はALLに置き換える
    trunk_vlans = want.get('trunk_vlans')
    if trunk_vlans == '1-4094':
      want['trunk_vlans'] = 'ALL'

    # VLAN番号はintに強制変換
    access_vlan = want.get('access_vlan')
    if access_vlan is not None and not isinstance(access_vlan, int):
      try:
        want['access_vlan'] = int(access_vlan)
      except ValueError:
        return 'access_vlan should be number, your input: {}'.format(access_vlan)

    # VLAN番号はintに強制変換
    native_vlan = want.get('native_vlan')
    if native_vlan is not None and not isinstance(native_vlan, int):
      try:
        want['nativce_vlan'] = int(native_vlan)
      except ValueError:
        return 'native_vlan should be number, your input: {}'.format(native_vlan)

    # modeがおかしくないかチェックする
    mode = want.get('mode')
    if mode is None or mode == 'access' or mode == 'trunk':
      pass
    else:
      return 'mode is supported only access or trunk. {}'.format(to_text(mode))

    # haveのパラメータと比較しておかしくないかチェックする
    switchport = have.get('switchport')
    if switchport != 'Enabled':
      return 'interface must be configured as switchport first.'

    channel_group = have.get('channel_group')
    if channel_group:
      return 'Can not change physical port because it is a port-channel member.'

    # vlan_listと比較しておかしくないかチェックする
    access_vlan = want.get('access_vlan')  # this is int
    native_vlan = want.get('native_vlan')  # this is int
    if access_vlan and access_vlan not in vlan_list:
      return 'You are trying to configure a access vlan on an interface that does not exist on the switch yet.'
    elif native_vlan and native_vlan not in vlan_list:
      return 'You are trying to configure a native vlan on an interface that does not exist on the switch yet.'


  def validate_list(self, want_list, have_list, vlan_list):
    if not have_list:
      return 'failed to investigate existing interfaces.'

    for want in want_list:

      # nameが省略表記されていても大丈夫なように正規化する
      name = want.get('name')
      norm_name = self.normalize_name(name)
      if norm_name != name:
        want['name_input'] = name
        want['name'] = norm_name
        name = norm_name

      state = want.get('state')
      # presentのときのみ検証する
      if state != 'present':
        continue

      have = self.search_obj_in_list(name, have_list)
      if have:
        msg = self.validate(want, have, vlan_list)
        if msg:
          return msg


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
      self._handle_template('show_vlan_path')
      self._handle_template('show_interfaces_switchport_path')
    except ValueError as e:
      return dict(failed=True, msg=to_text(e))

    # モジュールを実行する
    # ただし、このモジュールは何もしない
    result = super(ActionModule, self).run(task_vars=task_vars)

    #
    # モジュール実行後の後工程処理
    #

    # モジュールに渡されたパラメータ情報をオブジェクトにする
    want_list = self.map_params_to_obj()
    if self._task.args.get('debug'):
      result['want'] = want_list

    # コンフィグ情報をオブジェクトにしてhave_listにする
    if self._task.args.get('running_config_path'):
      config = self._task.args.get('running_config_path')
    else:
      config = self._task.args.get('running_config')

    if not config:
      return dict(failed=True, msg="running_config is required but not set")

    have_list = self.map_config_to_obj(config)

    # show interfaces switchportの出力をオブジェクトにしてswitchport_listにする
    if self._task.args.get('show_interfaces_switchport_path'):
      show_interfaces_switchport = self._task.args.get('show_interfaces_switchport_path')
    else:
      show_interfaces_switchport = self._task.args.get('show_interfaces_switchport')

    if not show_interfaces_switchport:
      return dict(failed=True, msg="show_interfaces_switchport is required but not set")

    switchport_list = self.map_show_interfaces_switchport_to_obj(show_interfaces_switchport)

    # switchport_listの情報をhave_listに追加する
    for item in have_list:
      o = self.search_obj_in_list(item.get('name'), switchport_list)
      if o:
        item.update(o)

    if self._task.args.get('debug'):
      result['have'] = have_list

    # show vlan briefの情報をオブジェクトにしてvlan_listにする
    if self._task.args.get('show_vlan_path'):
      show_vlan = self._task.args.get('show_vlan_path')
    else:
      show_vlan = self._task.args.get('show_vlan')

    vlan_list = self.map_show_vlan_to_obj(show_vlan)
    if self._task.args.get('debug'):
      result['vlan_list'] = vlan_list

    #
    # ここまでの処理でhave_list, want_list, vlan_listが出揃った
    #

    #
    # 入力条件がおかしくないかチェック
    #

    msg = self.validate_list(want_list, have_list, vlan_list)
    if msg:
      result['msg'] = msg
      result['failed'] = True

    #
    # 差分のコンフィグを作成する
    #

    commands = self.to_commands_list(want_list, have_list)
    result['commands'] = commands

    return result
