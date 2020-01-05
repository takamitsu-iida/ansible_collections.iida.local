#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = """
---
module: iida.local.ios_cfg
version_added: 2.9
author: "Takamitsu IIDA (@takamitsu-iida)"
short_description: Run commands on remote devices running Cisco IOS
description:
  - Sends arbitrary commands to an ios node.
options:
  lines:
    description:
      - The ordered set of commands that should be sent to the remote device.
    aliases: ['commands']

"""

EXAMPLES = r"""
"""

RETURN = """
commands:
  description: The set of commands that will be pushed to the remote device
  returned: always
  type: list

updates:
  description: The set of commands sent to the remote device
  returned: when commands was sent
  type: list
"""

from ansible.module_utils.network.ios.ios import ios_argument_spec
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.ios.ios import load_config


def main():
  """main entry point for module execution
  """

  argument_spec = dict(
    lines=dict(type='list', aliases=['commands'], required=True),
  )

  argument_spec.update(ios_argument_spec)

  module = AnsibleModule(
    argument_spec=argument_spec,
    supports_check_mode=True
  )

  result = {
    'changed': False,
  }

  lines = module.params['lines']

  result.update({
    'commands': lines,
    'updates': []
  })

  if lines:
    if not module.check_mode:
      load_config(module, lines)

      result.update({
        'changed': True,
        'updates': lines
      })

  module.exit_json(**result)


if __name__ == '__main__':
  main()
