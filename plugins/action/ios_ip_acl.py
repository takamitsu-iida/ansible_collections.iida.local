# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, missing-docstring

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import re

from ansible.plugins.action.normal import ActionModule as _ActionModule
from ansible.module_utils._text import to_text
from ansible.module_utils.six.moves.urllib.parse import urlsplit

try:
  # pylint: disable=unused-import
  from __main__ import display
except ImportError:
  # pylint: disable=ungrouped-imports
  from ansible.utils.display import Display
  display = Display()


class ActionModule(_ActionModule):

  #
  # 正規表現は将来拡張用の仮置き
  #

  PROTOCOL = r'''
    (?:\s+
      (?P<protocol>ip|tcp|udp)
      |
      (?:object-group\s+(?P<og>\S+))
    )
  '''

  SOURCE = r'''
    (?:\s+
      (?:host\s+(?P<src_host>\S+))
      |
      (?:object-group\s+(?P<src_og>\S+))
      |
      (?:(?P<src_any>any))
      |
      (?:(?P<src_network>\d+\.\d+\.\d+\.\d+)\s+(?P<src_hostmask>\d+\.\d+\.\d+\.\d+))
    )
  '''

  DESTINATION = r'''
    (?:\s+
      (?:host\s+(?P<dst_host>\S+))
      |
      (?:object-group\s+(?P<dst_og>\S+))
      |
      (?:(?P<dst_any>any))
      |
      (?:(?P<dst_network>\d+\.\d+\.\d+\.\d+)\s+(?P<dst_hostmask>\d+\.\d+\.\d+\.\d+))
    )
  '''

  SRC_PORT = r'''
    (?:
      (?:eq\s(?P<src_port>\d+))
      |
      (?:range\s+(?P<src_from>\d+)\s+(?P<src_to>\d+))
    )
  '''

  DST_PORT = r'''
    (?:
      (?:eq\s(?P<dst_port>\d+))
      |
      (?:range\s+(?P<dst_from>\d+)\s+(?P<dst_to>\d+))
    )
  '''

  _ACL = r'''
    ^access-list
    (?:\s+(P<name>\S+))   # name
    (?:\s+extended)
    (?:\s+(?P<action>permit|deny))
    {}  # protocol
    {}  # source
    {}  # src_port
    {}  # destination
    {}  # dst_port
  '''

  ACL = _ACL.format(PROTOCOL, SOURCE, SRC_PORT, DESTINATION, DST_PORT)

  RE_ACL = re.compile(ACL, re.VERBOSE)


  @staticmethod
  def sanitize(lines):
    results = []
    for line in lines:
      line = line.strip()
      if line:
        results.append(line)
    return results


  @staticmethod
  def check_remark(lines):
    for line in lines:
      if 'remark' in line:
        return True
    return False


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
      self._handle_template('show_access_list_path')
    except ValueError as e:
      return dict(failed=True, msg=to_text(e))

    # モジュールを実行する
    # ただし、このモジュールは何もしない
    result = super(ActionModule, self).run(task_vars=task_vars)

    #
    # モジュール実行後の後工程処理
    #

    # show access listの出力を取り出す
    if self._task.args.get('show_access_list_path'):
      show_access_list = self._task.args.get('show_access_list_path')
    else:
      show_access_list = self._task.args.get('show_access_list')

    # remove white space
    show_access_list_lines = self.sanitize(show_access_list.splitlines())

    acl_cli = self._task.args.get('acl_cli')
    if self.check_remark(acl_cli):
      result['failed'] = True
      result['msg'] = 'remark line detected in acl_cli.\n{}'.format(acl_cli)
      return result

    # access list commands to be pushed
    commands = []

    # create new config with sequence number
    acl_seq_lines = []
    for i, line in enumerate(acl_cli):
      acl_seq_lines.append(str((i+1)*10) + ' ' + line)

    # delete acl if not match
    for line in show_access_list_lines:
      line = re.sub(', wildcard bits', '', line)
      line = re.sub(' [(].{9,30}[)]', '', line)
      if line not in acl_seq_lines:
        commands.append('no ' + line)

    # add acl if not match
    for line in acl_seq_lines:
      if line not in show_access_list_lines:
        commands.append(line)

    result['commands'] = commands

    return result
