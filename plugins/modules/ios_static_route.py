#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.local.ios_static_route

short_description: IOS static route config generator

version_added: 2.9

description:
  - generate config from intent parameters and configured config

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against CSR1000v 16.03.06
  - Some static route parameters (multicast, global) are not supported.

options:

  running_config:
    description:
      - show running-config output on the remote device.
        'show running-config | include ip route' is prefered.
    required: True

  running_config_path:
    description:
      - file path to the running-config

  purge:
    description:
      - State of existing routes.
        When this argument is set to true, existing static routes
        which does not match with want routes will be deleted.
    default: false

  state:
    description:
      - State of the static route.
    default: present
    choices: ['present', 'absent']

  static_routes:
    description:
      - List of static route parameter.

  static_routes_cli:
    description:
      - List of static route as command line format.

  prefix:
    description:
      - prefix option in static route parameter

  netmask:
    description:
      - netmask option in static route parameter

  vrf:
    description:
      - vrf option in static route parameter

  nh_intf:
    description:
      - nh_intf option in static route parameter

  nh_addr:
    description:
      - nh_addr option in static route parameter

  dhcp:
    description:
      - dhcp option in static route parameter

  ad:
    description:
      - administrative distance option in static route parameter

  name:
    description:
      - name option in static route parameter

  permanent:
    description:
      - permanent option in static route parameter

  track:
    description:
      - track option in static route parameter

  tag:
    description:
      - tag option in static route parameter
'''

EXAMPLES = '''

- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  vars:

    running_config: |
      !
      ip route 0.0.0.0 0.0.0.0 172.20.0.1
      ip route 1.1.11.0 255.255.255.0 dhcp 250
      ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 name a track 1
      ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 permanent name a


  tasks:

    # - include_vars: vars/r1.yml

    #
    # TEST 1
    #
    - name: create config to be pushed
      iida.local.ios_static_route:
        running_config: "{{ running_config }}"
        # running_config_path: vars/sh_run_vlan.txt
        static_routes: "{{ static_routes }}"
        # debug: true
      register: r

      vars:
        static_routes:
          - prefix: 10.0.0.0
            netmask: 255.255.255.128
            nh_intf: GigabitEthernet2
            nh_addr: 172.28.128.100
            ad: 250
            tag: 1001
            permanent: false
            state: present

          - prefix: 10.0.0.0
            netmask: 255.255.255.0
            nh_intf: GigabitEthernet2
            nh_addr: 172.28.128.100
            state: present

    - name: TEST 1
      debug:
        var: r


    #
    # TEST 2
    #
    - name: create config to be pushed
      iida.local.ios_static_route:
        running_config: "{{ running_config }}"
        static_routes_cli: "{{ static_routes_cli }}"
        state: present
        # debug: true
      register: r

      vars:
        static_routes_cli:
          - ip route 10.0.0.0 255.0.0.0 GigabitEthernet2 172.28.128.1
          - ip route 10.0.0.0 255.255.0.0 GigabitEthernet2 172.28.128.1
          - ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.1

    - name: TEST 2
      debug:
        var: r

'''

RETURN = '''
commands:
  description: The list of configuration mode commands to send to the remotedevice
  returned: always
  type: list
  sample:
    - ip route 10.0.0.0 255.255.255.128 GigabitEthernet2 172.28.128.100 250 tag 1001
    - ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.100
'''

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.utils import remove_default_spec


def main():
  """main entry point for module execution
  """

  element_spec = dict(
    vrf=dict(type='str'),
    prefix=dict(type='str'),
    netmask=dict(type='str'),
    nh_intf=dict(type='str'),
    nh_addr=dict(type='str'),
    dhcp=dict(type='bool'),
    ad=dict(type='int'),
    name=dict(type='str'),
    permanent=dict(type='bool'),
    track=dict(type='int'),
    tag=dict(type='int'),
    state=dict(default='present', choices=['present', 'absent'])
  )

  # list of interfaces
  aggregate_spec = deepcopy(element_spec)
  aggregate_spec['prefix'] = dict(required=True)

  # remove default in aggregate spec, to handle common arguments
  remove_default_spec(aggregate_spec)

  argument_spec = dict(
    aggregate=dict(type='list', elements='dict', options=aggregate_spec),
    static_routes=dict(type='list'),
    static_routes_cli=dict(type='list'),
    running_config=dict(type='str'),
    running_config_path=dict(type='path'),
    purge=dict(default='False', type='bool'),
    debug=dict(type='bool')
  )

  argument_spec.update(element_spec)

  required_one_of = [
    ('prefix', 'aggregate', 'static_routes', 'static_routes_cli'),
    ('running_config', 'running_config_path')
  ]

  mutually_exclusive = [
    ('prefix', 'aggregate'),
    ('static_routes', 'static_routes_cli'),
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
