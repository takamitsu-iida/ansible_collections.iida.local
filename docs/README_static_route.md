# IOSのスタティックルート設定を生成するローカルモジュール

**iida.local.ios_static_route** はIOSのスタティックルートの設定コマンドを生成します。

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

- **static_routes** スタティックルートのパラメータをYAML形式(リスト)で指定します
- **static_routes_cli** IOSの設定コマンドそのものをリストで指定します
- **purge** 既存設定のうち希望するスタティックルートパラメータに一致しないものをまとめて削除します

<br>

### スタティックルート設定パラメータ

- **vrf** vrf名を文字列で指定します
- **prefix** A.B.C.Dでネットワークアドレスを指定します
- **netmask** A.B.C.Dでサブネットマスクを指定します
- **nh_intf** 次ホップアドレスに到達するためのインタフェースを指定します
- **nh_addr** 次ホップアドレスを指定します
- **dhcp** 経路をdhcpでもらうときに指定します
- **ad** administratively distanceです
- **tag** タグです
- **permanent** 次ホップへの到達性を確認しない場合に指定します
- **name** 経路の名前です
- **track** オブジェクトトラッキングの番号です

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

# スタティックルートの追加と削除

スタティックルートが何も設定されていない状態で以下のようなパラメータをモジュールに入力すると、

```yaml
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
```

以下の出力を得ます。

```json
"commands": [
    "ip route 10.0.0.0 255.255.255.128 GigabitEthernet2 172.28.128.100 250 tag 1001",
    "ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.100"
]
```

以下のようにスタティックルートが設定されている状態で、

```yaml
running_config: |
  !
  ip route 0.0.0.0 0.0.0.0 172.20.0.1
  ip route 1.1.11.0 255.255.255.0 dhcp 250
  ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 name a track 1
  ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 permanent name a
```

以下のようなパラメータをモジュールに入力すると、

```yaml
static_routes:
  - prefix: 1.1.11.0
    netmask: 255.255.255.0
    nh_intf: GigabitEthernet3
    nh_addr: 3.3.3.1
    state: present
```

以下の出力を得ます。
既存設定とはパラメータが異なるので単純に追加する結果になっています。
多くの場合、これは期待と違う動きだと思います。

```json
"commands": [
    "ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1"
]
```

同じパラメータであっても、モジュールに対して以下のように`purge`オプションを付けると、

```yaml
iida.local.ios_static_route:
  running_config: "{{ running_config }}"
  static_routes: "{{ static_routes }}"
  purge: true
```

以下のような出力が得られます。
全てのスタティックルートをYAMLで表現しておき、それに該当しないスタティックルートが設定されていたら削除する、という使い方ができます。

```json
"commands": [
    "ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1",
    "no ip route 0.0.0.0 0.0.0.0 172.20.0.1",
    "no ip route 1.1.11.0 255.255.255.0 dhcp 250",
    "no ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 name a track 1",
    "no ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 permanent name a"
],
```

入力をYAMLで表現するのが面倒な場合は、
以下のように`static_routes_cli`を使ってIOSの設定コマンドそのものをモジュールに入力することもできます。
purgeオプションを組み合わせると、管理が楽になると思います。

```yaml
static_routes_cli:
  - ip route 10.0.0.0 255.0.0.0 GigabitEthernet2 172.28.128.1
  - ip route 10.0.0.0 255.255.0.0 GigabitEthernet2 172.28.128.1
  - ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.1
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
        running_config: ""
        # running_config_path: vars/sh_run_vlan.txt
        static_routes: "{{ static_routes }}"
        debug: true
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
        # running_config_path: vars/sh_run_vlan.txt
        static_routes: "{{ static_routes }}"
        debug: true
      register: r

      vars:
        static_routes:
          - prefix: 1.1.11.0
            netmask: 255.255.255.0
            nh_intf: GigabitEthernet3
            nh_addr: 3.3.3.1
            state: present

    - name: TEST 2
      debug:
        var: r

    #
    # TEST 3
    #
    - name: create config to be pushed
      iida.local.ios_static_route:
        running_config: "{{ running_config }}"
        # running_config_path: vars/sh_run_vlan.txt
        static_routes: "{{ static_routes }}"
        debug: true
        purge: true
      register: r

      vars:
        static_routes:
          - prefix: 1.1.11.0
            netmask: 255.255.255.0
            nh_intf: GigabitEthernet3
            nh_addr: 3.3.3.1
            state: present

    - name: TEST 3
      debug:
        var: r

    #
    # TEST 4
    #
    - name: create config to be pushed
      iida.local.ios_static_route:
        running_config: "{{ running_config }}"
        static_routes_cli: "{{ static_routes_cli }}"
        state: present
        debug: true
      register: r

      vars:
        static_routes_cli:
          - ip route 10.0.0.0 255.0.0.0 GigabitEthernet2 172.28.128.1
          - ip route 10.0.0.0 255.255.0.0 GigabitEthernet2 172.28.128.1
          - ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.1

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
            "ip route 10.0.0.0 255.255.255.128 GigabitEthernet2 172.28.128.100 250 tag 1001",
            "ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.100"
        ],

TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1"
        ],

TASK [TEST 3]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1",
            "no ip route 0.0.0.0 0.0.0.0 172.20.0.1",
            "no ip route 1.1.11.0 255.255.255.0 dhcp 250",
            "no ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 name a track 1",
            "no ip route 1.1.11.0 255.255.255.0 GigabitEthernet3 3.3.3.1 250 tag 1 permanent name a"
        ],

TASK [TEST 4]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "ip route 10.0.0.0 255.0.0.0 GigabitEthernet2 172.28.128.1",
            "ip route 10.0.0.0 255.255.0.0 GigabitEthernet2 172.28.128.1",
            "ip route 10.0.0.0 255.255.255.0 GigabitEthernet2 172.28.128.1"
        ],
```
