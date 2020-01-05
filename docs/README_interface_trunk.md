# CatalystのインタフェースのVLAN設定を生成するローカルモジュール

**iida.local.ios_interface_trunk** はCatalystのインタフェースにVLANを設定するコマンドを生成します。

> **ローカルモジュールとは**
>
> 事前に採取しておいたコンフィグおよび希望する状態を入力すると、その状態にするための設定コマンドを出力するモジュールです。
> 対象装置への接続は必要ありません。
> 事前に投入するコマンドをレビューしたい場合に便利です。

物理ポートがチャネルを構成している場合はfailed=trueを返します。
チャネルを構成している場合は物理ポートではなくポートチャネルインタフェースに設定してください。

<br>

## モジュールへの入力

### 既存の設定を指定するパラメータ

これら２つは排他で、running_config_pathが優先されます。

- **running_config** 既存設定(show running-config vlan)を文字列として指定します
- **running_config_path** 既存設定(show running-config vlan)を保存したファイルへのパスを指定します

show interfaces switchportの出力も必要です。

- **show_interfaces_switchport** `show interfaces switchport`出力を文字列として指定します
- **show_interfaces_switchport_path** `show interfaces switchport`出力を保存したファイルへのパスを指定します

show vlanの出力も必要です。

- **show_vlan** `show vlan`出力を文字列として指定します
- **show_vlan_path** `show vlan`出力を保存したファイルへのパスを指定します

<br>

### 希望する設定を指定するパラメータ

- **interfaces** インタフェースのVLAN状態をYAML形式で指定します

<br>

### インタフェース設定パラメータ

- **mode** インタフェースのモードをaccessかtrunkで指定します
- **access_vlan** VLAN IDを数値で指定します(1-4094)
- **trunk_vlan** allowed vlanに含めるVLANを'-'と','で指定します
- **native_vlan** native vlanを指定します(1-4094)
- **state** インタフェースにおけるVLANの状態を[ 'present' | 'absent' | 'unconfigured' ]で指定します

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## インタフェースへのVLANの追加・削除

何も設定されていない物理ポートに対して、

```yaml
running_config: |
  !
  interface GigabitEthernet0/28
  !
```

以下のようなパラメータをモジュールに入力すると、

```yaml
- name: GigabitEthernet0/28
  mode: access
  access_vlan: 2
  state: present
```

以下の出力を得ます。

```json
"commands": [
    "interface GigabitEthernet0/28",
    "switchport mode access",
    "switchport access vlan 2"
]
```

以下のような入力パラメータをモジュールに入力すると、

```yaml
interfaces:
  - name: GigabitEthernet0/28
    mode: trunk
    nonegotiate: true
    native_vlan: 3
    trunk_vlans: 2-3,5,7-9
    state: present
```

以下の出力を得ます。

```json
"commands": [
    "interface GigabitEthernet0/28",
    "switchport trunk encapsulation dot1q",
    "switchport mode trunk",
    "switchport trunk allowed vlan 2-3,5,7-9",
    "switchport trunk native vlan 3",
    "switchport nonegotiate"
]
```

以下のように設定されている物理ポートに対して、

```yaml
running_config: |
  !
  interface GigabitEthernet0/27
    switchport trunk encapsulation dot1q
    switchport trunk allowed vlan 2
    switchport mode trunk
  !
```

以下のようなパラメータをモジュールに入力すると、

```yaml
- name: GigabitEthernet0/27
  state: unconfigured
```

以下の出力を得ます。

```json
"commands": [
    "interface GigabitEthernet0/27",
    "no switchport trunk encapsulation",
    "no switchport nonegotiate",
    "no switchport mode",
    "no switch access vlan",
    "no switchport trunk native vlan",
    "no switchport trunk allowed vlan"
]
```

## プレイブックの例

```yaml
---

- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    show_vlan: |
      VLAN Name                             Status    Ports
      ---- -------------------------------- --------- -------------------------------
      1    default                          active    Gi0/25, Gi0/26, Gi0/27, Gi0/28
      2    VLAN0002                         active    Gi0/1, Gi0/2, Gi0/3, Gi0/4, Gi0/5, Gi0/6
                                                      Gi0/7, Gi0/8, Gi0/9, Gi0/10, Gi0/11, Gi0/12
      3    VLAN0003                         active    Gi0/13, Gi0/14, Gi0/15, Gi0/16, Gi0/17
                                                      Gi0/18, Gi0/19, Gi0/20, Gi0/21, Gi0/22
                                                      Gi0/23, Gi0/24
      4    VLAN0004                         active
      5    VLAN0005                         active
      6    VLAN0006                         active
      7    VLAN0007                         active
      8    VLAN0008                         active
      9    VLAN0009                         active
      85   VLAN0085                         active
      1002 fddi-default                     act/unsup
      1003 token-ring-default               act/unsup
      1004 fddinet-default                  act/unsup
      1005 trnet-default                    act/unsup


    show_interfaces_switchport: |
      Name: Gi0/27
      Switchport: Enabled
      Administrative Mode: trunk
      Operational Mode: down
      Administrative Trunking Encapsulation: dot1q
      Negotiation of Trunking: On
      Access Mode VLAN: 1 (default)
      Trunking Native Mode VLAN: 1 (default)
      Administrative Native VLAN tagging: enabled
      Voice VLAN: none
      Administrative private-vlan host-association: none
      Administrative private-vlan mapping: none
      Administrative private-vlan trunk native VLAN: none
      Administrative private-vlan trunk Native VLAN tagging: enabled
      Administrative private-vlan trunk encapsulation: dot1q
      Administrative private-vlan trunk normal VLANs: none
      Administrative private-vlan trunk associations: none
      Administrative private-vlan trunk mappings: none
      Operational private-vlan: none
      Trunking VLANs Enabled: 2
      Pruning VLANs Enabled: 2-1001
      Capture Mode Disabled
      Capture VLANs Allowed: ALL
      Protected: false
      Unknown unicast blocked: disabled
      Unknown multicast blocked: disabled
      Appliance trust: none

      Name: Gi0/28
      Switchport: Enabled
      Administrative Mode: dynamic auto
      Operational Mode: down
      Administrative Trunking Encapsulation: negotiate
      Negotiation of Trunking: On
      Access Mode VLAN: 1 (default)
      Trunking Native Mode VLAN: 1 (default)
      Administrative Native VLAN tagging: enabled
      Voice VLAN: none
      Administrative private-vlan host-association: none
      Administrative private-vlan mapping: none
      Administrative private-vlan trunk native VLAN: none
      Administrative private-vlan trunk Native VLAN tagging: enabled
      Administrative private-vlan trunk encapsulation: dot1q
      Administrative private-vlan trunk normal VLANs: none
      Administrative private-vlan trunk associations: none
      Administrative private-vlan trunk mappings: none
      Operational private-vlan: none
      Trunking VLANs Enabled: ALL
      Pruning VLANs Enabled: 2-1001
      Capture Mode Disabled
      Capture VLANs Allowed: ALL
      Protected: false
      Unknown unicast blocked: disabled
      Unknown multicast blocked: disabled
      Appliance trust: none


    running_config: |
      !
      interface GigabitEthernet0/27
       switchport trunk encapsulation dot1q
       switchport trunk allowed vlan 2
       switchport mode trunk
      !
      interface GigabitEthernet0/28
      !


  tasks:

    # - include_vars: vars/c3560g.yml

    #
    # TEST 1
    #
    - name: create config to be pushed
      iida.local.ios_interface_trunk:
        running_config: "{{ running_config }}"
        show_vlan: "{{ show_vlan }}"
        show_interfaces_switchport: "{{ show_interfaces_switchport }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          #
          # アクセスポートに指定する
          #
          - name: GigabitEthernet0/28
            mode: access
            access_vlan: 2
            state: present

    - name: TEST 1
      debug:
        var: r


    #
    # TEST 2
    #
    - name: create config to be pushed
      iida.local.ios_interface_trunk:
        running_config: "{{ running_config }}"
        show_vlan: "{{ show_vlan }}"
        show_interfaces_switchport: "{{ show_interfaces_switchport }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          #
          # すでに入っている設定を消して未設定状態にする
          #
          - name: GigabitEthernet0/27
            state: unconfigured

    - name: TEST 2
      debug:
        var: r


    #
    # TEST 3
    #
    - name: create config to be pushed
      iida.local.ios_interface_trunk:
        running_config: "{{ running_config }}"
        show_vlan: "{{ show_vlan }}"
        show_interfaces_switchport: "{{ show_interfaces_switchport }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          #
          # trunkの設定
          #
          - name: GigabitEthernet0/28
            mode: trunk
            nonegotiate: true  # falseを指定すると、存在しないのが正しい状態になる
            native_vlan: 3
            trunk_vlans: 2-3,5,7-9
            # trunk_vlans: 2,4,6,8
            # trunk_vlans: 1,5,10-4094
            # trunk_vlans: 2-4,6-9
            # trunk_vlans: ALL
            state: present

    - name: TEST 3
      debug:
        var: r


    #
    # TEST 4
    #
    - name: create config to be pushed
      iida.local.ios_interface_trunk:
        running_config: "{{ running_config }}"
        show_vlan: "{{ show_vlan }}"
        show_interfaces_switchport: "{{ show_interfaces_switchport }}"
        interfaces: "{{ interfaces }}"
      register: r

      vars:
        interfaces:
          #
          # 指定したvlanがトランクの中に存在しない状態にする（その他はそのままなので、現状を把握してる場合のみ使うこと）
          #
          - name: GigabitEthernet0/28
            mode: trunk
            trunk_vlans: 2
            state: absent

    - name: TEST 4
      debug:
        var: r
```

<br>

# 実行結果

```bash
TASK [TEST 1]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface GigabitEthernet0/28",
            "switchport mode access",
            "switchport access vlan 2"
        ],
        "failed": false
    }
}

TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface GigabitEthernet0/27",
            "no switchport trunk encapsulation",
            "no switchport nonegotiate",
            "no switchport mode",
            "no switch access vlan",
            "no switchport trunk native vlan",
            "no switchport trunk allowed vlan"
        ],
        "failed": false
    }
}

TASK [TEST 3]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface GigabitEthernet0/28",
            "switchport trunk encapsulation dot1q",
            "switchport mode trunk",
            "switchport trunk allowed vlan 2-3,5,7-9",
            "switchport trunk native vlan 3",
            "switchport nonegotiate"
        ],
        "failed": false
    }
}

TASK [TEST 4]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface GigabitEthernet0/28",
            "switchport trunk allowed vlan remove 2"
        ],
        "failed": false
    }
}
```
