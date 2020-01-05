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

try:
  from ipaddress import ip_address  #, ip_network
  HAS_IPADDRESS = True
except ImportError:
  HAS_IPADDRESS = False


class ActionModule(_ActionModule):

  supported_params = ['vrf', 'prefix', 'netmask', 'nh_intf', 'nh_addr', 'dhcp', 'ad', 'tag', 'permanent', 'name', 'track']

  # The order of regex is very important.
  #
  # example
  #   ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 name a track 1
  #   ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 permanent name a
  #
  # options not supported
  #  - multicast
  #  - global

  # this regex is originaly from ciscoconfparse
  # https://github.com/mpenning/ciscoconfparse
  #
  IP_ROUTE = r'''
    ^ip\s+route                                                  # ip route
    (?:\s+(?:vrf\s+(?P<vrf>\S+)))?                               # vrf
    \s+
    (?P<prefix>\d+\.\d+\.\d+\.\d+)                               # prefix
    \s+
    (?P<netmask>\d+\.\d+\.\d+\.\d+)                              # netmask
    (?:\s+(?P<nh_intf>[^\d|dhcp|tag|name|track|permanent]\S+))?  # next hop interface
    (?:\s+(?P<nh_addr>\d+\.\d+\.\d+\.\d+))?                      # next hop address
    (?:\s+(?P<dhcp>dhcp))?                                       # DHCP
    (?:\s+(?P<ad>\d+))?                                          # administrative distance
    (?:\s+tag\s+(?P<tag>\d+))?                                   # tag
    (?:\s+(?P<permanent>permanent))?                             # permanent
    (?:\s+name\s+(?P<name>\S+))?                                 # name
    (?:\s+track\s+(?P<track>\d+))?                               # track
  '''

  RE_IP_ROUTE = re.compile(IP_ROUTE, re.VERBOSE)

  # pylint: disable=C0301
  _IPV6_REGEX_STR_COMPRESSED1 = r"""(?!:::\S+?$)(?P<addr1>(?P<opt1_1>{0}(?::{0}){{7}})|(?P<opt1_2>(?:{0}:){{1}}(?::{0}){{1,6}})|(?P<opt1_3>(?:{0}:){{2}}(?::{0}){{1,5}})|(?P<opt1_4>(?:{0}:){{3}}(?::{0}){{1,4}})|(?P<opt1_5>(?:{0}:){{4}}(?::{0}){{1,3}})|(?P<opt1_6>(?:{0}:){{5}}(?::{0}){{1,2}})|(?P<opt1_7>(?:{0}:){{6}}(?::{0}){{1,1}})|(?P<opt1_8>:(?::{0}){{1,7}})|(?P<opt1_9>(?:{0}:){{1,7}}:)|(?P<opt1_10>(?:::)))""".format(r'[0-9a-fA-F]{1,4}')
  _IPV6_REGEX_STR_COMPRESSED2 = r"""(?!:::\S+?$)(?P<addr2>(?P<opt2_1>{0}(?::{0}){{7}})|(?P<opt2_2>(?:{0}:){{1}}(?::{0}){{1,6}})|(?P<opt2_3>(?:{0}:){{2}}(?::{0}){{1,5}})|(?P<opt2_4>(?:{0}:){{3}}(?::{0}){{1,4}})|(?P<opt2_5>(?:{0}:){{4}}(?::{0}){{1,3}})|(?P<opt2_6>(?:{0}:){{5}}(?::{0}){{1,2}})|(?P<opt2_7>(?:{0}:){{6}}(?::{0}){{1,1}})|(?P<opt2_8>:(?::{0}){{1,7}})|(?P<opt2_9>(?:{0}:){{1,7}}:)|(?P<opt2_10>(?:::)))""".format(r'[0-9a-fA-F]{1,4}')
  _IPV6_REGEX_STR_COMPRESSED3 = r"""(?!:::\S+?$)(?P<addr3>(?P<opt3_1>{0}(?::{0}){{7}})|(?P<opt3_2>(?:{0}:){{1}}(?::{0}){{1,6}})|(?P<opt3_3>(?:{0}:){{2}}(?::{0}){{1,5}})|(?P<opt3_4>(?:{0}:){{3}}(?::{0}){{1,4}})|(?P<opt3_5>(?:{0}:){{4}}(?::{0}){{1,3}})|(?P<opt3_6>(?:{0}:){{5}}(?::{0}){{1,2}})|(?P<opt3_7>(?:{0}:){{6}}(?::{0}){{1,1}})|(?P<opt3_8>:(?::{0}){{1,7}})|(?P<opt3_9>(?:{0}:){{1,7}}:)|(?P<opt3_10>(?:::)))""".format(r'[0-9a-fA-F]{1,4}')

  IPV6_ROUTE = r'''
    ^ipv6\s+route
    (?:\s+vrf\s+(?P<vrf>\S+))?
    (?:\s+(?P<prefix>{0})\/(?P<masklength>\d+))                               # prefix
    (?:(?:\s+(?P<nh_addr1>{1})) | (?:\s+(?P<nh_intf>\S+(?:\s+\d\S*?\/\S+)?)(?:\s+(?P<nh_addr2>{2}))?))
    (?:\s+nexthop-vrf\s+(?P<nexthop_vrf>\S+))?
    (?:\s+(?P<ad>\d+))?                                                       # Administrative distance
    (?:\s+(?:(?P<ucast>unicast)|(?P<mcast>multicast)))?
    (?:\s+tag\s+(?P<tag>\d+))?                                                # Route tag
  '''.format(_IPV6_REGEX_STR_COMPRESSED1, _IPV6_REGEX_STR_COMPRESSED2, _IPV6_REGEX_STR_COMPRESSED3)

  RE_IPV6_ROUTE = re.compile(IPV6_ROUTE, re.VERBOSE)


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
  def bool_to_str(obj, key):
    v = obj.get(key)
    if v and isinstance(v, bool):
      obj[key] = key


  def validate_prefix(self, obj):
    value = obj.get('prefix')
    if value is None:
      return 'prefix is required.'
    try:
      ip_address(value)
    except ValueError as e:
      return 'prefix: {}'.format(to_text(e))


  def validate_nh_addr(self, obj):
    value = obj.get('nh_addr')
    if value is None:
      if obj.get('dhcp') is None:
        return 'nh_addr or dhcp is required.'
    else:
      try:
        ip_address(value)
      except ValueError as e:
        return 'nh_addr: {}'.format(to_text(e))


  def validate_nh_intf(self, obj):
    name = obj.get('nh_intf')
    norm_name = self.normalize_name(name)
    if norm_name != name:
      obj['nh_intf'] = norm_name


  def validate_netmask(self, obj):
    value = obj.get('netmask')
    if value is None:
      return 'netmask is required.'
    try:
      prefixlen = sum([bin(int(x)).count('1') for x in value.split('.')])
      if prefixlen > 32 or prefixlen < 0:
        return 'wrong prefix: {}'.format(value)
    except ValueError as e:
      return 'netmask: {}'.format(to_text(e))


  def validate_ad(self, obj):
    key = 'ad'
    value = obj.get(key)
    if value is not None:
      if isinstance(value, int):
        # overwrite as str
        value = str(value)
        obj[key] = value
      try:
        i = int(value)
        if i < 1 or i > 255:
          return 'ad shoud be in range [1-255]: {}'.format(value)
      except ValueError as e:
        return '{}: {}'.format(key, to_text(e))


  def validate_tag(self, obj):
    key = 'tag'
    value = obj.get(key)
    if value is not None:
      if isinstance(value, int):
        # overwrite as str
        value = str(value)
        obj[key] = value
      try:
        i = int(value)
        if i < 1 or i > 4294967295:
          return 'tag shoud be in range [1-4294967295]: {}'.format(value)
      except ValueError as e:
        return '{}: {}'.format(key, to_text(e))


  def validate_track(self, obj):
    key = 'track'
    value = obj.get(key)
    if value is not None:
      if isinstance(value, int):
        # overwrite as str
        value = str(value)
        obj[key] = value
      try:
        i = int(value)
        if i < 1 or i > 1000:
          return 'track shoud be in range [1-1000]: {}'.format(value)
      except ValueError as e:
        return '{}: {}'.format(key, to_text(e))


  def validate(self, want_list):
    for want in want_list:
      # dhcp and nh_addr is mutually exclusive
      if want.get('dhcp') and want.get('nh_addr'):
        return 'dhcp and next hop address are mutually exclusive.'

      # permanent and track is mutually exclusive
      if want.get('permanent') and want.get('track'):
        return 'permanent and track are mutually exclusive.'

      # convert bool to str
      self.bool_to_str(want, 'dhcp')
      self.bool_to_str(want, 'permanent')

      # check by validate function
      for key in want.keys():
        # to avoid pylint E1102
        # validator = getattr(self, 'validate_{}'.format(key), None)
        validator = getattr(self, 'validate_%s' % key, None)
        if callable(validator):
          msg = validator(want)
          if msg:
            return msg


  def search_obj_in_list(self, want, have_list):
    for have in have_list:
      if self.equals_to(want, have):
        return have
    return None


  def equals_to(self, want, have):
    # prefix, netmask, nh_intf, nh_addr, ad

    for key in self.supported_params:
      if want.get(key) != have.get(key):
        return False
    return True


  def map_config_to_obj(self, config):
    results = []
    for line in config.splitlines():
      if line.startswith('ip route'):
        obj = self.cli_to_obj(line)
        if obj:
          results.append(obj)
    return results


  def cli_to_obj(self, line):
    match = self.RE_IP_ROUTE.search(line)
    if match:
      obj = match.groupdict()
      obj['line'] = line
      return obj
    return None


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
    """convert module parameters to object

    Returns:
      list -- list of interface parameters
    """

    results = []

    # cliコマンドを渡された場合
    static_routes_cli = self._task.args.get('static_routes_cli')
    if static_routes_cli:
      if isinstance(static_routes_cli, str):
        static_routes_cli = list(static_routes_cli)
      for item in static_routes_cli:
        obj = self.cli_to_obj(item)
        if obj:
          obj['state'] = self._task.args.get('state', 'present')
          results.append(obj)
      return results

    # 一覧を渡された場合
    static_routes = self._task.args.get('static_routes')
    if static_routes and isinstance(static_routes, list):
      for item in static_routes:
        obj = self.args_to_obj(item)
        results.append(obj)
      return results

    # aggregateとして複数渡された場合
    aggregate = self._task.args.get('aggregate')
    if aggregate and isinstance(aggregate, list):
      for item in aggregate:
        # パラメータオブジェクトを作成してからaggregateの内容を追記する
        obj = self.args_to_obj(self._task.args)
        obj.update(item)
        results.append(obj)
      return results

    # パラメータだけが指定された場合
    obj = self.args_to_obj(self._task.args)
    results.append(obj)

    return results


  @staticmethod
  def obj_to_cli(obj):
    cmd = 'ip route '

    if obj.get('vrf'):
      cmd += 'vrf {} '.format(obj.get('vrf'))

    cmd += '{} '.format(obj.get('prefix'))
    cmd += '{} '.format(obj.get('netmask'))

    if obj.get('nh_intf'):
      cmd += '{} '.format(obj.get('nh_intf'))

    if obj.get('dhcp'):
      cmd += 'dhcp '
      if obj.get('ad'):
        cmd += obj.get('ad')
      return cmd.strip()

    if obj.get('nh_addr'):
      cmd += '{} '.format(obj.get('nh_addr'))

    if obj.get('ad'):
      cmd += '{} '.format(obj.get('ad'))

    if obj.get('tag'):
      cmd += 'tag {} '.format(obj.get('tag'))

    if obj.get('permanent'):
      cmd += 'permanent '

    if obj.get('name'):
      cmd += 'name {} '.format(obj.get('name'))

    if obj.get('track'):
      cmd += 'track {} '.format(obj.get('track'))

    return cmd.strip()


  def to_commands(self, want_list, have_list):
    commands = []

    for want in want_list:
      state = want.get('state')
      have = self.search_obj_in_list(want, have_list)
      if state == 'present':
        if have:
          # すでにその経路は存在するので何もしない
          have['action'] = 'keep'
        else:
          cli = self.obj_to_cli(want)
          commands.append(cli)

      if state == 'absent':
        if have:
          have['action'] = 'delete'
          commands.append('no {}'.format(have.get('line')))
        else:
          # already deleted
          pass

    purge = self._task.args.get('purge', False)
    for have in have_list:
      action = have.get('action')
      if purge and action is None:
        commands.append('no {}'.format(have.get('line')))

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

    if not HAS_IPADDRESS:
      return dict(failed=True, msg='ipaddress python package is required')

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

    commands = self.to_commands(want_list, have_list)
    result['commands'] = commands

    # for debug purpose
    if self._task.args.get('debug'):
      result['want'] = want_list
      result['have'] = have_list

    return result
