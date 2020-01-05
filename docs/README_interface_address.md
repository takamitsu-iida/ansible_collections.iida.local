# IOSのIPアドレス設定を生成するローカルモジュール

**iida.local.ios_interface_address** はIOSのIPアドレス設定のコマンドを生成します。

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
- **ipv4** IPアドレスをA.B.C.D/Nの形式で指定します
- **ipv4_secondary** セカンダリIPアドレスをA.B.C.D/Nの形式で指定します

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## IPアドレスの追加・削除

<br>

以下の設定は、

```yaml
interfaces:
  - name: GigabitEthernet3
    ipv4: 3.3.3.3/24
    ipv4_secondary:
      - 33.33.33.1/32
    state: present
```

以下のコマンドを生成します。

```bash
"commands": [
    "interface GigabitEthernet5",
    "ip address 3.3.3.3 255.255.255.0",
    "ip address 33.33.33.1 255.255.255.255 secondary",
],
```

IPアドレスを消したい場合、以下のようにipv4キーの値を消すか、

```yaml
interfaces:
  - name: GigabitEthernet3
    ipv4:
    ipv4_secondary:
      - 33.33.33.1/32
    state: present
```

もしくは以下のようにstateをabsentにします。

```yaml
interfaces:
  - name: GigabitEthernet3
    ipv4: 3.3.3.3/24
    state: absent
```

stateをabsentにした場合、どのセカンダリを消して、どれを残して、という管理が発生しますのでおすすめできません。
presentを使ってパラメータの値を空白にすることで削除した方がよいでしょう。

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
        debug: true
      register: r

      vars:
        interfaces:
          - name: GigabitEthernet3
            ipv4: 3.3.3.3/24
            ipv4_secondary:
              - 33.33.33.1/24
            state: present

          - name: GigabitEthernet4
            ipv4: 4.4.4.4/24
            ipv4_secondary:
              - 44.44.44.44/24
            state: present

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
            "ip address 33.33.33.1 255.255.255.0 secondary",
            "interface GigabitEthernet4",
            "no ip address 44.44.44.44 255.255.255.0",
            "ip address 4.4.4.4 255.255.255.0",
            "ip address 44.44.44.44 255.255.255.0 secondary"
        ],
```
