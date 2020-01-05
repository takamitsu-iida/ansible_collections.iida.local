#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.local.ios_interface_address

short_description: IOS interface config generator

version_added: 2.9

description:
  - generate config from intent config and configured config

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against CSR1000v 16.03.06

options:
  running_config:
    description:
      - show running-config output on the remote device
    required: True
'''

EXAMPLES = '''
- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    running_config: |
      !
      interface Loopback0
       ip address 192.168.254.1 255.255.255.255
      !
      interface GigabitEthernet3
       ip address 33.33.33.33 255.255.255.0 secondary
       ip address 3.3.3.3 255.255.255.0
       negotiation auto
       cdp enable
       no mop enabled
       no mop sysid
      !
      interface GigabitEthernet4
       ip address 44.44.44.44 255.255.255.0
       negotiation auto
       cdp enable
       no mop enabled
       no mop sysid
      !

  tasks:

    #
    # TEST 1
    #
    - name: create config to be pushed
      iida.local.ios_interface_address:
        running_config: "{{ running_config }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          - name: GigabitEthernet3
            ipv4:
              - 3.3.3.1/24
              - 33.33.33.1/24 secondary
            state: present

          - name: GigabitEthernet4
            ipv4:
              - 4.4.4.4/24
              - 44.44.44.44/24 secondary
            state: present

    - name: TEST 1
      debug:
        var: r

    #
    # TEST 2
    #
    - name: create config to be pushed
      iida.local.ios_interface_address:
        running_config: "{{ running_config }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          - name: GigabitEthernet3
            ipv4:
            state: absent

          - name: GigabitEthernet4
            ipv4:
            state: absent

    - name: TEST 2
      debug:
        var: r
'''

RETURN = '''
commands:
  description: The list of configuration mode commands to send to the remotedevice
  returned: always
  type: list
'''

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.utils import remove_default_spec


def main():
  """main entry point for module execution
  """

  element_spec = dict(
    state=dict(default='present', choices=['present', 'absent']),
    name=dict(type='str'),
    ipv4=dict(type='str'),
    ipv4_secondary=dict(type='list'),
    ipv6=dict(type='str'),
    purge=dict(type='bool')
  )

  # list of interfaces
  aggregate_spec = deepcopy(element_spec)
  aggregate_spec['name'] = dict(required=True)

  # remove default in aggregate spec, to handle common arguments
  remove_default_spec(aggregate_spec)

  argument_spec = dict(
    aggregate=dict(type='list', elements='dict', options=aggregate_spec),
    interfaces=dict(type='list'),
    running_config=dict(type='str'),
    running_config_path=dict(type='path'),
    debug=dict(type='bool')
  )

  argument_spec.update(element_spec)

  required_one_of = [
    ('interfaces', 'name', 'aggregate'),
    ('running_config', 'running_config_path')
  ]

  mutually_exclusive = [
    ('name', 'aggregate'),
    ('running_config', 'running_config_path')
  ]

  module = AnsibleModule(
    argument_spec=argument_spec,
    required_one_of=required_one_of,
    mutually_exclusive=mutually_exclusive,
    supports_check_mode=True)

  result = {'changed': False}

  module.exit_json(**result)


if __name__ == '__main__':
  main()
