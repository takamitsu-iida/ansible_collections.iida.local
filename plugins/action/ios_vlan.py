# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-docstring

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import re

from ansible.module_utils.six.moves.urllib.parse import urlsplit
from ansible.plugins.action.normal import ActionModule as _ActionModule
from ansible.module_utils._text import to_text
from ansible.module_utils.network.common.config import NetworkConfig

try:
  # pylint: disable=unused-import
  from __main__ import display
except ImportError:
  # pylint: disable=ungrouped-imports
  from ansible.utils.display import Display
  display = Display()


class ActionModule(_ActionModule):

  supported_params = ('vlan_id', 'vlan_range', 'vlan_name')


  @staticmethod
  def search_obj_in_list(vlan_id, lst):
    if not isinstance(vlan_id, str):
      vlan_id = str(vlan_id)

    for o in lst:
      if str(o.get('vlan_id')) == vlan_id:
        return o
    return None


  @staticmethod
  def vlan_str_to_list(vlan_str):
    if vlan_str is None:
      return None

    if not isinstance(vlan_str, str):
      vlan_str = str(vlan_str)

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

    parent = 'vlan {}'.format(name)

    cfg = configobj[parent]
    cfg = '\n'.join(cfg.children)

    match = re.search(r'{} (.+)$'.format(arg), cfg, re.M)
    if match:
      return match.group(1)


  def map_config_to_obj(self, config):

    # running-configの情報からvlan_idやvlan_nameを抽出する

    results = []

    match = re.findall(r'^vlan (\d+\S*)', config, re.M)
    if not match:
      return results

    configobj = NetworkConfig(indent=1, contents=config)

    for item in set(match):
      item = str(item)

      vlan_id = None
      vlan_range = None
      if item.isdigit():
        vlan_id = item
      else:
        vlan_range = item

      vlan_name = self.parse_config_argument(configobj, item, 'name')

      obj = {
        'vlan_id': vlan_id,
        'vlan_range': vlan_range,
        'vlan_name': vlan_name,
        'state': 'present'
      }
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

    # vlansを渡された場合
    vlans = self._task.args.get('vlans')
    if vlans:
      for item in vlans:
        obj = self.args_to_obj(item)
        results.append(obj)
      return results

    obj = self.args_to_obj(self._task.args)
    results.append(obj)

    return results


  def to_commands_list(self, want_list, have_list):
    commands = []

    want_present_list, want_absent_list = self.to_vlan_list(want_list)
    have_present_list, _ = self.to_vlan_list(have_list)

    # add vlan
    add_list = set(want_present_list).difference(have_present_list)
    if add_list:
      add_list = sorted(add_list)
      add_vlan_str = self.vlan_list_to_str(add_list)
      if add_vlan_str:
        commands.append('vlan {}'.format(add_vlan_str))
        commands.append('exit')

    # delete vlan
    del_list = set(have_present_list).intersection(want_absent_list)
    if del_list:
      del_list = sorted(del_list)
      del_vlan_str = self.vlan_list_to_str(del_list)
      if del_vlan_str:
        commands.append('no vlan {}'.format(del_vlan_str))

    # change vlan_name
    for want in want_list:
      if want.get('state') == 'absent':
        continue

      vlan_id = want.get('vlan_id')
      if not vlan_id:
        continue
      if not isinstance(vlan_id, str):
        vlan_id = str(vlan_id)

      want_vlan_name = want.get('vlan_name')

      have = self.search_obj_in_list(vlan_id, have_list)
      if have:
        have_vlan_name = have.get('vlan_name')
        if want_vlan_name != have_vlan_name:
          if not want_vlan_name:
            commands.append('vlan {}'.format(vlan_id))
            commands.append('no name')
            commands.append('exit')
          else:
            commands.append('vlan {}'.format(vlan_id))
            commands.append('name {}'.format(want_vlan_name))
            commands.append('exit')
      elif want_vlan_name:
        commands.append('vlan {}'.format(vlan_id))
        commands.append('name {}'.format(want_vlan_name))
        commands.append('exit')

    return commands


  def validate(self, want_list):
    # convert int to str
    for want in want_list:
      vlan_id = want.get('vlan_id')
      if vlan_id and isinstance(vlan_id, int):
        want['vlan_id'] = str(vlan_id)

      vlan_range = want.get('vlan_range')
      if vlan_range and isinstance(vlan_range, int):
        want['vlan_range'] = str(vlan_range)

      name = want.get('vlan_name')
      if name and isinstance(name, int):
        want['vlan_name'] = str(name)
      if name and ' ' in name:
        return 'You can not include space as vlan_name, {}'.format(name)

    present_list, absent_list = self.to_vlan_list(want_list)
    common = set(present_list).intersection(set(absent_list))
    if common:
      return 'You can not set present and absent on the same time, vlan {}'.format(str(common))


  def to_vlan_list(self, obj_list):
    present_vlans = []
    absent_vlans = []

    for item in obj_list:
      if item.get('vlan_id'):
        vlan_id = str(item.get('vlan_id'))
        if item.get('state') == 'present':
          present_vlans.append(vlan_id)
        elif item.get('state') == 'absent':
          absent_vlans.append(vlan_id)
      elif item.get('vlan_range'):
        vlan_range = item.get('vlan_range')
        if item.get('state') == 'present':
          present_vlans.append(vlan_range)
        elif item.get('state') == 'absent':
          absent_vlans.append(vlan_range)

    present_vlans = sorted(present_vlans)
    absent_vlans = sorted(absent_vlans)

    present_list = self.vlan_str_to_list(','.join(present_vlans))
    absent_list = self.vlan_str_to_list(','.join(absent_vlans))

    return present_list, absent_list


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

    # コンフィグ情報をオブジェクトにしてhave_listにする
    if self._task.args.get('running_config_path'):
      config = self._task.args.get('running_config_path')
    else:
      config = self._task.args.get('running_config')

    have_list = self.map_config_to_obj(config)
    if self._task.args.get('debug'):
      result['have'] = have_list

    # モジュールに渡されたパラメータ情報をオブジェクトにする
    want_list = self.map_params_to_obj()
    if self._task.args.get('debug'):
      result['want'] = want_list

    #
    # ここまでの処理でhave_list, want_listが出揃った
    #

    #
    # 条件がおかしくないかをチェックする
    #

    msg = self.validate(want_list)
    if msg:
      result['msg'] = msg
      result['failed'] = True

    #
    # 差分のコンフィグを作成する
    #

    commands = self.to_commands_list(want_list, have_list)
    result['commands'] = commands

    return result
