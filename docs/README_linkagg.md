# Catalystのリンクアグリゲーション設定を生成するローカルモジュール

**iida.local.ios_linkagg** はCatalystのリンクアグリゲーションを設定するコマンドを生成します。

> **ローカルモジュールとは**
>
> 事前に採取しておいたコンフィグおよび希望する状態を入力すると、その状態にするための設定コマンドを出力するモジュールです。
> 対象装置への接続は必要ありません。
> 事前に投入するコマンドをレビューしたい場合に便利です。

<br>

## モジュールへの入力

### 既存の設定を指定するパラメータ

これら２つは排他で、running_config_pathが優先されます。

- **running_config** 既存設定(show running-config vlan)を文字列として指定します
- **running_config_path** 既存設定(show running-config vlan)を保存したファイルへのパスを指定します

<br>

### 希望する設定を指定するパラメータ

- **port_channels** ポートチャネルの設定パラメータをYAML形式で指定します

<br>

### ポートチャネル設定パラメータ

- **mode** ポートチャネルのモードを['active', 'on', 'passive', 'auto', 'desirable']で指定します
- **group** チャネルグループ番号を指定します(物理ポートに設定するchannel-groupの番号)
- **members** ポートチャネルを構成する物理ポート名（フルネーム）をリストで指定します
- **state** インタフェースにおけるVLANの状態を['present' | 'absent']で指定します

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## リンクアグリゲーションの追加・削除

何も設定されていない物理ポート(Gig0/27-28)に対して以下のようなパラメータをモジュールに入力すると、

```yaml
port_channels:
  - group: 1
    mode: active
    members:
      - GigabitEthernet0/27
      - GigabitEthernet0/28
```

以下の出力を得ます。

```json
"commands": [
    "interface port-channel 1",
    "exit",
    "interface GigabitEthernet0/27",
    "channel-group 1 mode active",
    "exit",
    "interface GigabitEthernet0/28",
    "channel-group 1 mode active",
    "exit"
]
```

以下のように設定されているリンクアグリゲーションに対して、

```yaml
running_config: |
  !
  interface GigabitEthernet0/27
    channel-group 1 mode on
  !
  interface GigabitEthernet0/28
    channel-group 1 mode on
  !
  interface Port-channel1
  !
```

以下のようなパラメータをモジュールに入力すると、

```yaml
port_channels:
  - group: 1
    mode: active
    members:
      - GigabitEthernet0/27
      - GigabitEthernet0/28
```

以下の出力を得ます。
モードがonからactiveに変わっているため、一度設定を削除して改めてチャネルグループを設定しています。

```json
"commands": [
    "interface GigabitEthernet0/27",
    "no channel-group",
    "exit",
    "interface GigabitEthernet0/28",
    "no channel-group",
    "exit",
    "interface GigabitEthernet0/27",
    "channel-group 1 mode active",
    "exit",
    "interface GigabitEthernet0/28",
    "channel-group 1 mode active",
    "exit"
]
```

<br>

## プレイブックの例

```yaml
---

- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    running_config: |
      !
      vlan 10,20,30
      no spannning-tree vlan 10,20,30
      !
      interface GigabitEthernet0/27
       channel-group 1 mode on
      !
      interface GigabitEthernet0/28
       channel-group 1 mode on
      !
      interface Port-channel1
       switchport trunk encapsulation dot1q
       switchport trunk allowed vlan 10,20,30
       switchport mode trunk
      !

  tasks:

    #
    # TEST 1
    #

    - name: create config to be pushed
      iida.local.ios_linkagg:
        running_config: ""
        port_channels: "{{ port_channels }}"
        state: present
        debug: true
      register: r

      vars:
        port_channels:
          - group: 1
            mode: active
            members:
              - GigabitEthernet0/27
              - GigabitEthernet0/28

    - name: TEST 2
      debug:
        var: r

    #
    # TEST 2
    #

    - name: create config to be pushed
      iida.local.ios_linkagg:
        running_config: "{{ running_config }}"
        port_channels: "{{ port_channels }}"
        state: present
        debug: true
      register: r

      vars:
        port_channels:
          - group: 1
            mode: active
            members:
              - GigabitEthernet0/27
              - GigabitEthernet0/28

    - name: TEST 2
      debug:
        var: r
```

<br>

# 実行結果

```bash
TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface port-channel 1",
            "exit",
            "interface GigabitEthernet0/27",
            "channel-group 1 mode active",
            "exit",
            "interface GigabitEthernet0/28",
            "channel-group 1 mode active",
            "exit"
        ],

TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "interface GigabitEthernet0/28",
            "no channel-group",
            "exit",
            "interface GigabitEthernet0/27",
            "no channel-group",
            "exit",
            "interface GigabitEthernet0/27",
            "channel-group 1 mode active",
            "exit",
            "interface GigabitEthernet0/28",
            "channel-group 1 mode active",
            "exit"
        ],
```
