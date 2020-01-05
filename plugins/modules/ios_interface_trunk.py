#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.local.ios_interface_trunk

short_description: IOS interface config generator

version_added: 2.9

description:
  - generate config from intent config and configured config

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against Catalyst 3560G

options:
  running_config:
    description:
      - show running-config output on the remote device
    required: True

  running_config_path:
    description:
      - file path to the running-config
    required: True

  show_vlan:
    description:
      - show vlan outut on the remote device
    required: True

  show_vlan_path:
    description:
      - file path to the show vlan output
    required: True

  show_interfaces_switchport
    description:
      - show interfaces switchport on the remote device
    required: True

  show_interfaces_switchport_path
    description:
      - file path to the show interfaces switchport output
    required: True

  interfaces:
    description:
      - variable to specify intent config.
    required: True
'''

EXAMPLES = '''

playbook

- name: gather information on the remote device
  ios_command:
    commands:
      - show running-config
      - show vlan
      - show interfaces switchport
  register: output

- name: create config to be pushed
  iida.local.ios_interface_trunk:
    running_config: "{{ output.stdout[0] }}"
    show_vlan: "{{ output.stdout[1] }}"
    show_interfaces_switchport : "{{ output.stdout[2] }}"
    interfaces: "{{ interfaces }}"
    debug: true
  register: r

- name: apply config to the remote device
  ios_config:
    lines: "{{ commands }}"
    match: none
  register: r


vars file is like this.

interfaces:

  # access port
  - name: GigabitEthernet0/27
    mode: access
    access_vlan: 2
    state: present

  # trunk port
  - name: GigabitEthernet0/28
    mode: trunk
    nonegotiate: true
    native_vlan: 3
    # trunk_vlans: 2-3,5,7-9
    # trunk_vlans: 2,4,6,8
    # trunk_vlans: 1,5,10-4094
    trunk_vlans: 2-4,6-9
    # trunk_vlans: ALL
    state: present

  # remove specific vlan from the trunk
  - name: GigabitEthernet0/28
    mode: trunk
    trunk_vlans: 2
    state: absent

  # clear config
  - name: GigabitEthernet0/28
    state: unconfigured

'''

RETURN = '''
commands:
  description: The list of configuration mode commands to send to the remotedevice
  returned: always
  type: list
  sample:
    - interface GigabitEthernet0/5
    - switchport trunk allowed vlan 2-3
'''

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.utils import remove_default_spec


def main():
  """main entry point for module execution
  """

  element_spec = dict(
    name=dict(type='str'),
    state=dict(default='present', choices=['present', 'absent', 'unconfigured']),
    mode=dict(choices=['access', 'trunk']),
    access_vlan=dict(type='int'),
    native_vlan=dict(type='int'),
    trunk_vlans=dict(type='str'),
    nonegotiate=dict(type='bool')
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
    show_vlan=dict(type='str'),
    show_vlan_path=dict(type='path'),
    show_interfaces_switchport=dict(type='str'),
    show_interfaces_switchport_path=dict(type='path'),
    debug=dict(type='bool')
  )

  argument_spec.update(element_spec)

  required_one_of = [
    ('interfaces', 'name', 'aggregate'),
    ('running_config', 'running_config_path'),
    ('show_vlan', 'show_vlan_path'),
    ('show_interfaces_switchport', 'show_interfaces_switchport_path')
  ]

  mutually_exclusive = [
    ('name', 'aggregate'),
    ('access_vlan', 'trunk_vlans'),
    ('access_vlan', 'native_vlan'),
    ('running_config', 'running_config_path'),
    ('show_vlan', 'show_vlan_path'),
    ('show_interfaces_switchport', 'show_interfaces_switchport_path')
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
