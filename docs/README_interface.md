# IOSのインタフェース設定を生成するローカルモジュール

**iida.local.ios_interface** はIOSのインタフェース設定コマンドを生成します。

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

- **interfaces** 対象インタフェースの配列です

<br>

### インタフェース設定パラメータ

- **name** インタフェース名のフルネーム（略記不可）
- **description** descriptionコマンド
- **negotiation** negotiationコマンド
- **speed** speed設定
- **duplex** duplex設定(CSR1000vは未サポート)
- **mtu** mtu設定(機器によってサポートされる値が違う)
- **shutdown** shutdown設定

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## state設定の考え方

presentは存在することを期待し、absentは存在しないことを期待します。

以下の設定はdescriptionが'configured by ansible'と設定されていることを期待します。

```yaml
- name: Loopback0
  description: configured by ansible
  state: present
```

以下の設定はdescriptionがNoneの状態になっていることを期待します。
結果としてdescription設定は削除されます。

```yaml
- name: Loopback0
  description:
  state: present
```

以下の設定はdescriptionという項目が **存在しない** ことを期待します。
結果としてdescription設定は削除されます。

```yaml
- name: Loopback0
  description:
  state: absent
```

以下の設定はLoopback0そのものが **存在しない** ことを期待します。
結果としてLoopback0は削除されます。

```yaml
- name: Loopback0
  state: absent
```

以下の設定はGigabitEthernet3そのものが **存在しない** ことを期待します。
が、物理インタエースは削除できませんので、結果としては何も起こりません。
削除されうるのは論理インタフェース(LoopbackおよびTunnelのみ)です。

```yaml
- name: GigabitEthernet3
  state: absent
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
      interface Loopback0
       ip address 192.168.254.1 255.255.255.255
      !
      interface GigabitEthernet3
       description configured by hand
       ip address 33.33.33.33 255.255.255.0
       no negotiation auto
       speed 1000
       cdp enable
       mtu 1512
       no mop enabled
       no mop sysid
      !
      interface GigabitEthernet4
       description configured by hand
       ip address 44.44.44.44 255.255.255.0
       negotiation auto
       cdp enable
       no mop enabled
       no mop sysid
      !

    interfaces:

      - name: GigabitEthernet3
        description: configured by ansible
        negotiation:
        speed:
        # duplex: is not supported on CSR1000v
        # duplex:
        mtu: 1512
        shutdown: false
        state: present

      - name: GigabitEthernet4
        negotiation: false
        speed: 1000
        state: present

      - name: Loopback0
        description: configured by ansible
        shutdown: true
        state: present


  tasks:

    # - include_vars: vars/r1.yml

    #
    # TEST 1
    #

    - name: create config to be pushed
      iida.local.ios_interface:
        running_config: "{{ running_config }}"
        interfaces: "{{ interfaces }}"
        debug: true
      register: r

    - name: TEST 1
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
            "interface GigabitEthernet3",
            "no description",
            "description configured by ansible",
            "mtu 1512",
            "interface GigabitEthernet4",
            "no negotiation auto",
            "speed 1000",
            "interface Loopback0",
            "description configured by ansible",
            "shutdown"
        ],
```
