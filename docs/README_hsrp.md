# IOSのHSRP設定を生成するローカルモジュール

**iida.local.ios_hsrp** はIOSのHSRP設定コマンドを生成します。

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

### HSRP設定パラメータ

- **name** インタフェース名のフルネーム（略記不可）
- **group** HSRPグループ番号
- **priority** HSRPプライオリティ値（デフォルト100）
- **vip** HSRP仮想IP
- **secondary** セカンダリHSRP仮想IP（リスト）
- **preempt** preempt（['enabled', 'disabled']）
- **delay_minimum** standby 1 preempt delay minimum 60
- **delay_reload** standby 1 preempt delay reload 120
- **delay_sync**  standby 1 preempt delay sync 30
- **auth_type** 認証タイプ（['text', 'md5']）
- **auth_string** 認証文字列
- **track** オブジェクトトラッキング番号 standby 1 track 1
- **track_decrement** プライオリティを下げる数 standby 1 track 1 decrement 10

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## HSRP設定

HSRPが設定されていないインタフェースに対して以下の設定を入力すると、

```yaml
interfaces:
  - name: GigabitEthernet5
    group: 1
    version: 2
    priority: 100
    preempt: enabled
    vip: 3.3.3.1
    secondary:
      - 3.3.3.254
    auth_type: text
    auth_string: cisco
    track: 1
    track_decrement: 10
    state: present
```

以下の設定コマンドを生成します。

```bash
"commands": [
    "interface GigabitEthernet5",
    "standby version 2",
    "standby 1 ip 3.3.3.1",
    "standby 1 ip 3.3.3.254 secondary",
    "standby 1 preempt",
    "standby 1 track 1 decrement 10",
    "exit"
]
````

既にHSRPが設定されているインタフェースで消したいパラメータがあるときはキーのみを指定します。
以下の設定ではversionの値が存在しない状態を期待しますので、結果としてバージョン設定は削除されます（no standby 1 version）。

```yaml
interfaces:
  - name: GigabitEthernet5
    group: 1
    version:
    state: present
```

必要なパラメータだけを列挙するのではなく、全てのパラメータを列挙して不要なものは値を消しておくのがよいでしょう。

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
      interface GigabitEthernet3
       description 2018-08-14T09:28:49Z
       ip address 3.3.3.3 255.255.255.0
       standby version 2
       standby 1 ip 3.3.3.1
       standby 1 ip 3.3.3.250 secondary
       standby 1 ip 3.3.3.254 secondary
       standby 1 preempt delay minimum 60 reload 180 sync 60
       standby 1 authentication cisco2
       negotiation auto
       no mop enabled
       no mop sysid
      !
      interface GigabitEthernet4
       description 2018-08-14T09:28:49Z
       ip address 4.4.4.4 255.255.255.0
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
        vip: 3.3.3.2  # 変更
        secondary:
          - 3.3.3.250
          - 3.3.3.253
        auth_type: text
        auth_string: cisco
        state: present
        purge: true

      - name: GigabitEthernet4
        group: 1
        version: 1
        vip: 4.4.4.1
        auth_type: md5
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
            "standby 1 ip 3.3.3.2",
            "standby 1 ip 3.3.3.253 secondary",
            "no standby 1 ip 3.3.3.254 secondary",
            "no standby 1 preempt delay",
            "standby 1 preempt",
            "no standby 1 authentication",
            "exit",
            "interface GigabitEthernet4",
            "standby 1 ip 4.4.4.1",
            "standby 1 authentication md5 key-string cisco",
            "exit"
        ],
```
