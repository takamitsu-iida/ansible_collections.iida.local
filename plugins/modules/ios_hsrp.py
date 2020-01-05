#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.local.ios_hsrp

short_description: IOS hsrp route config generator

version_added: 2.9

description:
  - generate config from intent parameters and configured config

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against CSR1000v 16.03.06
  - hsrp without group number is not supported
  - standby 1 authentication md5 key-chain, is not supported
  - standby 1 track shutdown, is not supported

options:
  running_config:
    description:
      - show running-config output on the remote device.
      - One of the running_config and running_config_path is required.
    required: True

  running_config_path:
    description:
      - file path to the running-config

  name:
    description:
      - Full name of interface that is being managed for HSRP.
    required: true

  group:
    description:
      - HSRP group number.
    required: true

  version:
    description:
      - HSRP version.
    default: '1'
    choices: ['1','2']

  priority:
    description:
      - HSRP priority
    default: '100'

  preempt:
    description:
      - Enable/Disable preempt.
    choices: ['enabled', 'disabled']

  vip:
    description:
      - HSRP virtual IP address

  secondary:
    description:
      - HSRP seondary virtual IP address
    type: list

  auth_string:
    description:
      - Authentication string.

  auth_type:
    description:
      - Authentication type.
    choices: ['text','md5']

  interfaces:
    description:
      - list of interfaces HSRP should be configured.

  state:
    description:
      - Specify desired state of the resource.
    choices: ['present','absent']
    default: 'present'
'''

EXAMPLES = '''
- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    running_config: |
      !
      interface GigabitEthernet3
       description 2018-08-14T09:28:49Z
       ip address 3.3.3.3 255.255.255.0
       standby version 2
       standby 1 ip 3.3.3.1
       standby 1 ip 3.3.3.250 secondary
       standby 1 ip 3.3.3.254 secondary
       standby 1 preempt delay minimum 60 reload 180 sync 60
       standby 1 authentication cisco2
       standby 2 ip 3.3.3.253
       standby 2 priority 110
       standby 2 preempt
       negotiation auto
       no mop enabled
       no mop sysid
      !
      interface GigabitEthernet4
       description 2018-08-14T09:28:49Z
       ip address 4.4.4.4 255.255.255.0
       standby 1 ip 4.4.4.1
       standby 1 authentication md5 key-string cisco
       negotiation auto
       no mop enabled
       no mop sysid
      !

    interfaces:
      - name: GigabitEthernet3
        group: 1
        version: 2
        priority: 100
        preempt: enabled
        delay_minimum: 60
        delay_reload: 120
        delay_sync: 30
        vip: 3.3.3.1
        secondary:
          - 3.3.3.254
          - 3.3.3.253
        auth_type: text
        auth_string: cisco
        state: present

  tasks:

    #
    # TEST 1
    #

    - name: create config to be pushed
      iida.local.ios_hsrp:
        running_config: "{{ running_config }}"
        interfaces: "{{ interfaces }}"
        debug: true
      register: r

    - name: TEST 1
      debug:
        var: r
'''

RETURN = '''
commands:
  description: commands sent to the device
  returned: always
  type: list
'''

from ansible.module_utils.basic import AnsibleModule


def main():
  """main entry point for module execution
  """

  element_spec = dict(
    name=dict(type='str'),
    group=dict(type='str'),
    version=dict(choices=['1', '2'], default='1'),
    priority=dict(type='str'),
    preempt=dict(type='str', choices=['disabled', 'enabled']),
    delay_minimum=dict(type='str'),
    delay_reload=dict(type='str'),
    delay_sync=dict(type='str'),
    vip=dict(type='str'),
    secondary=dict(type='list'),
    auth_type=dict(choices=['text', 'md5']),
    auth_string=dict(type='str'),
    state=dict(default='present', choices=['present', 'absent', 'unconfigured'])
  )

  argument_spec = dict(
    running_config=dict(type='str'),
    running_config_path=dict(type='path'),
    interfaces=dict(type='list'),
    debug=dict(type='bool')
  )

  argument_spec.update(element_spec)

  required_one_of = [
    ('name', 'interfaces'),
    ('running_config', 'running_config_path')
  ]

  mutually_exclusive = [
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
