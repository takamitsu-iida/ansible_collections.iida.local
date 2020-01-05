#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.local.ios_ip_acl

short_description: IOS ip access-list config generator

version_added: 2.9

description:
  - generate config from intent config and configured config

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against CSR1000v 16.03.06

options:
  show_access_list:
    description:
      - show access-list output configured on the remote device
    required: True

  acl_lines:
    description:
      - intent config of ip access-list
    required: True
'''

EXAMPLES = '''
- name: create config to be pushed
  local_action:
    module: iida.local.ios_ip_acl
    show_access_list: "{{ output.stdout[0] }}"
    acl_lines: "{{ acl_lines }}"
  register: r

- set_fact:
    change_lines: "{{ r.commands }}"
'''

RETURN = '''
commands:
  description: The configuration lines to be pushed to the remote device
  returned: always
  type: list
  sample: |
    [
      "10 permit ip 192.168.10.0 0.0.0.255 any",
      "20 permit ip 192.168.20.0 0.0.0.255 any",
      "30 permit ip 192.168.30.0 0.0.0.255 any",
      "40 permit ip 192.168.50.0 0.0.0.255 any",
      "50 permit ip 192.168.40.0 0.0.0.255 any",
      "60 permit tcp 192.168.1.0 0.0.0.255 host 1.1.1.1 eq www",
      "70 permit tcp 192.168.1.0 0.0.0.255 host 1.1.1.1 eq 443",
      "80 permit tcp 192.168.1.0 0.0.0.255 host 1.1.1.1 eq 3389",
      "90 permit tcp 192.168.1.0 0.0.0.255 host 2.2.2.2 eq 3389",
      "100 permit icmp any any",
      "110 deny ip any any"
    ]
'''

from ansible.module_utils.basic import AnsibleModule


def main():
  """main entry point for module execution
  """

  argument_spec = dict(
    show_access_list=dict(type='str'),
    show_access_list_path=dict(type='path'),
    acl_cli=dict(type='list', required=True),
    debug=dict(default=False, types='bool')
  )

  required_one_of = [
    ('show_access_list', 'show_access_list_path')
  ]

  mutually_exclusive = [
    ('show_access_list', 'show_access_list_path')
  ]

  module = AnsibleModule(
    argument_spec=argument_spec,
    required_one_of=required_one_of,
    mutually_exclusive=mutually_exclusive,
    supports_check_mode=True)

  result = {
    'changed': False
  }

  module.exit_json(**result)


if __name__ == '__main__':
  main()
