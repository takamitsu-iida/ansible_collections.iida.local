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

  supported_params = [
    'description',
    'negotiation',
    'speed',
    'duplex',
    'mtu',
    'shutdown'
  ]


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


  def is_logical_interface(self, intf_name):
    logical_interface_list = ['loopback', 'tunnel']
    for name in logical_interface_list:
      if self.is_interface(intf_name, name):
        return True
    return False


  def is_interface(self, intf_name, name):
    intf_name = intf_name.lower()
    if intf_name.startswith(name):
      return True
    return False


  def _NOT_USED_validate_mtu(self, want):
    # The mtu command is not always supported.
    # For example catalyst does not support mtu on physical interface.
    key = 'mtu'
    value = want.get(key)
    if isinstance(value, str):
      if not value.isnumeric():
        return 'mtu should be number {}'.format(value)
      try:
        value = int(value)
        want[key] = value
      except ValueError as e:
        return 'mtu: {}'.format(to_text(e))
    if value and not 64 <= int(value) <= 9600:
      return 'mtu must be between 64 and 9600'


  def validate_negotiation(self, want):
    key = 'negotiation'
    value = want.get(key)
    if value:
      if isinstance(value, str):
        if value == 'auto':
          value = True
          want[key] = value
        else:
          return 'negotiation must be boolean: {}'.format(value)


  def validate_speed(self, want):
    key = 'speed'
    value = want.get(key)
    if value:
      negotiation = want.get('negotiation')
      if negotiation is not False:
        return 'To set speed {}, disable auto negotiation first.'.format(str(value))


  def validate_duplex(self, want):
    key = 'duplex'
    value = want.get(key)
    if value:
      negotiation = want.get('negotiation')
      if negotiation is not False:
        return 'To set duplex {}, disable auto negotiation first.'.format(str(value))


  def validate(self, want_list):
    for want in want_list:

      # nameが省略表記されていても大丈夫なように正規化する
      name = want.get('name')
      norm_name = self.normalize_name(name)
      if norm_name != name:
        want['name_input'] = name
        want['name'] = norm_name

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


  def parse_config_argument(self, configobj, name, arg=None):

    # nameで指定したインタフェース配下のコンフィグを取り出す
    parent = 'interface {}'.format(name)
    cfg = configobj[parent]
    cfg = '\n'.join(cfg.children)

    # 正規表現argに一致し、その後ろに続く文字列を返す
    match = re.search(r'{} (.+)$'.format(arg), cfg, re.M)
    if match:
      return match.group(1)


  def parse_description(self, configobj, name):
    return self.parse_config_argument(configobj, name, 'description')


  # negotiation autoは否定するとno negotiation autoが表示されるという変わった作り
  def parse_negotiation(self, configobj, name):
    cfg = configobj['interface {}'.format(name)]
    cfg = '\n'.join(cfg.children)
    match = re.search(r'^negotiation auto', cfg, re.M)
    return bool(match)


  def parse_speed(self, configobj, name):
    return self.parse_config_argument(configobj, name, 'speed')


  def parse_duplex(self, configobj, name):
    return self.parse_config_argument(configobj, name, 'duplex')


  def parse_mtu(self, configobj, name):
    return self.parse_config_argument(configobj, name, 'mtu')


  # shutdownは引数を取らないので特殊
  def parse_shutdown(self, configobj, name):
    cfg = configobj['interface {}'.format(name)]
    cfg = '\n'.join(cfg.children)
    match = re.search(r'^shutdown', cfg, re.M)
    return bool(match)


  def map_config_to_obj(self, config):

    # コンフィグからインタフェース名の一覧を取り出す
    match = re.findall(r'^interface (\S+)', config, re.M)
    if not match:
      return list()

    configobj = NetworkConfig(indent=1, contents=config)

    results = []
    for intf_name in set(match):
      obj = {}
      obj['name'] = intf_name
      obj['state'] = 'present'

      for param in self.supported_params:
        func = getattr(self, 'parse_%s' % param, None)
        if callable(func):
          obj[param] = func(configobj, intf_name)

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

    # インタフェースのパラメータ一覧を渡された場合
    interfaces = self._task.args.get('interfaces')
    if interfaces and isinstance(interfaces, list):
      for item in interfaces:
        obj = self.args_to_obj(item)
        obj['name'] = item.get('name')
        results.append(obj)
      return results

    # 一覧を渡された場合
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
    obj['name'] = self._task.args.get('name')
    results.append(obj)

    return results

  #
  # メモ
  # absent_XXX(want, have)
  #  haveは必ず存在する
  #  wantにXXXキーは存在する
  #

  def absent_description(self, want, have):
    key = 'description'
    if key not in want:
      return None

    commands = []

    if have.get(key) is not None:
      commands.append('no description')

    return commands

  #
  # メモ
  # present_XXX(want, have)
  #  haveはNoneの場合もある
  #  wantにXXXキーは存在する
  #

  def present_description(self, want, have):
    commands = []

    key = 'description'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)

      # 比較して適切なコマンドを返却
      if have_value is not None and want_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          commands.append('no {}'.format(key))
          commands.append('{} {}'.format(key, want_value))
      elif have_value is not None and want_value is None:
        # 既存には設定されているが、希望する値が空っぽなので、現状維持
        pass
      elif have_value is None and want_value is not None:
        # 既存には設定されておらず、希望する値が指示されている
        commands.append('{} {}'.format(key, want_value))
      elif have_value is None and want_value is None:
        pass

    else:
      # 論理インタフェースを新規作成する場合はhaveがNoneになる
      if want_value:
        return '{} {}'.format(key, want_value)

    return commands


  def absent_negotiation(self, want, have):
    key = 'negotiation'
    if key not in want:
      return None

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    if have.get(key) is not None:
      commands.append('negotiation auto')
    return commands


  def present_negotiation(self, want, have):
    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    key = 'negotiation'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)
      if have_value is not None and want_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          if want_value is True:
            commands.append('negotiation auto')
          else:
            commands.append('no negotiation auto')
      elif have_value is not None and want_value is None:
        pass
      elif have_value is None and want_value is not None:
        if want_value is True:
          commands.append('negotiation auto')
        else:
          commands.append('no negotiation auto')
      elif have_value is None and want_value is None:
        pass

    else:
      # 論理インタフェースを新規作成する場合はhaveがNoneになる
      if want_value:
        commands.append('negotiation auto')
      else:
        commands.append('no negotiation auto')

    return commands


  def absent_speed(self, want, have):
    key = 'speed'
    if key not in want:
      return None

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    if have.get(key) is not None:
      commands.append('no speed')

    return commands


  def present_speed(self, want, have):

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    key = 'speed'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)
      if want_value is not None and have_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          commands.append('{} {}'.format(key, want_value))
      elif have_value is not None and want_value is None:
        # 既存には設定されているが、希望する値が空っぽなので、現状維持
        pass
      elif have_value is None and want_value is not None:
        # 既存には設定されておらず、希望する値が指示されている
        commands.append('{} {}'.format(key, want_value))
      elif have_value is None and want_value is None:
        pass
    else:
      # 論理インタフェースを新規作成するとき
      if want_value:
        commands.append('{} {}'.format(key, want_value))

    return commands


  def absent_duplex(self, want, have):

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    key = 'duplex'
    if have.get(key) is not None:
      commands.append('no duplex')

    return commands


  def present_duplex(self, want, have):

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    key = 'duplex'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)
      if have_value is not None and want_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          commands.append('{} {}'.format(key, want_value))
      elif have_value is not None and want_value is None:
        # 既存には設定されているが、希望する値が空っぽなので、現状維持
        pass
      elif have_value is None and want_value is not None:
        # 既存には設定されておらず、希望する値が指示されている
        commands.append('{} {}'.format(key, want_value))
      elif have_value is None and want_value is None:
        pass
    else:
      # コマンド生成
      if want_value:
        commands.append('{} {}'.format(key, want_value))

    return commands


  def absent_mtu(self, want, have):

    # loopbak does not support mtu
    if self.is_interface(want.get('name'), 'loopback'):
      return None

    commands = []

    key = 'mtu'
    if have.get(key) is not None:
      commands.append('no mtu')

    return commands


  def present_mtu(self, want, have):

    if self.is_logical_interface(want.get('name')):
      return None

    commands = []

    key = 'mtu'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)
      if have_value is not None and want_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          commands.append('{} {}'.format(key, want_value))
      elif have_value is not None and want_value is None:
        # 既存には設定されているが、希望する値が空っぽなので、既存はいじらない
        pass
      elif have_value is None and want_value is not None:
        # 既存には設定されておらず、希望する値が指示されている
        commands.append('{} {}'.format(key, want_value))
      elif have_value is None and want_value is None:
        pass
    else:
      # コマンド生成
      if want_value:
        commands.append('{} {}'.format(key, want_value))

    return commands


  def absent_shutdown(self, want, have):
    key = 'shutdown'
    if key not in want:
      return None

    commands = []

    if have.get(key) is not None:
      commands.append('no shutdown')

    return commands


  def present_shutdown(self, want, have):
    commands = []

    key = 'shutdown'
    want_value = want.get(key)

    if have:
      have_value = have.get(key)
      if have_value is not None and want_value is not None:
        # 既存も希望も共に値があるなら、一致するかを比較する
        if want_value == have_value:
          pass
        else:
          if want_value is True:
            commands.append('{}'.format(key))
          else:
            commands.append('no {}'.format(key))
      elif have_value is not None and want_value is None:
        # 既存には設定されているが、希望する値が空っぽなので、既存はいじらない
        pass
      elif have_value is None and want_value is not None:
        # 既存には設定されておらず、希望する値が指示されている
        if want_value is True:
          commands.append('{}'.format(key))
      elif have_value is None and want_value is None:
        pass
    else:
      # コマンド生成
      if want_value:
        commands.append('shutdown')

    return commands


  def to_commands_present(self, want, have):
    commands = []

    name = want.get('name')
    interface = 'interface {}'.format(name)
    commands.append(interface)

    # call self.present_param()
    for param in self.supported_params:
      # wantにキーがある場合、すなわちYAMLで指示されているなら、
      if param in want:
        func = getattr(self, 'present_%s' % param, None)
        if callable(func):
          cmds = func(want, have)
          if cmds:
            commands.extend(cmds)

    if commands and commands[-1] == interface:
      commands.pop(-1)

    return commands


  def to_commands_absent(self, want, have):
    commands = []
    intf_name = want.get('name')

    # wantにパラメータが何も指定されていないならインタフェースをまるごと削除する
    # ただし、対象は論理インタフェースのみ
    if not set(self.supported_params) & set(want.keys()):
      # loopbackとtunnelインタフェースを削除する
      if have:
        if self.is_logical_interface(intf_name):
          commands.append('no interface {}'.format(intf_name))
      return commands

    # wantのパラメータをabsent状態にする

    interface = 'interface {}'.format(intf_name)
    commands.append(interface)

    for param in self.supported_params:
      # wantにキーがある場合、すなわちYAMLでパラメータが書かれてさえいれば削除する
      if param in want:
        func = getattr(self, 'absent_%s' % param, None)
        if callable(func):
          cmds = func(want, have)
          if cmds:
            commands.extend(cmds)

    if commands and commands[-1] == interface:
      commands.pop(-1)

    return commands


  def to_commands(self, want, have):
    state = want.get('state')

    if state == 'absent':
      # 削除する対象が存在するときだけ実行
      if have:
        return self.to_commands_absent(want, have)
    elif state == 'present':
      # 論理インタフェースを新規で作成することもあるのでhaveがNoneのときでも実行する
      return self.to_commands_present(want, have)


  def to_commands_list(self, want_list, have_list):
    commands = []

    for want in want_list:
      intf_name = want.get('name')
      have = self.search_obj_in_list(intf_name, have_list)
      cmds = self.to_commands(want, have)
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
