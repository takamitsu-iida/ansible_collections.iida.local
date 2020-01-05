# IOSのIPアクセスリスト設定を生成するローカルモジュール

**iida.local.ios_ip_access_list** はIOSのIPアクセスリストを設定するコマンドを生成します。

> **ローカルモジュールとは**
>
> 事前に採取しておいたコンフィグおよび希望する状態を入力すると、その状態にするための設定コマンドを出力するモジュールです。
> 対象装置への接続は必要ありません。
> 事前に投入するコマンドをレビューしたい場合に便利です。

このモジュールはparentが`ip access-list "{{ acl_type }}" "{{ acl_name }}"`となっている中身の`access-list`コマンドの順序制御を行います。

まだ汎用性が低いので機能拡張予定です。

<br>

## モジュールへの入力

### 既存の設定を指定するパラメータ

これら２つは排他で、show_access_list_pathが優先されます。

- **show_access_list** 既存のアクセスリスト設定(show access-lists {{ acl_name }} | include ^ +[1-9])を文字列として指定します
- **show_access_list_path** 既存のアクセスリスト設定(show access-lists {{ acl_name }} | include ^ +[1-9])を保存したファイルへのパスを指定します

<br>

### 希望する設定を指定するパラメータ

- **acl_cli** アクセスリストの設定コマンドをYAML形式（リスト）で指定します

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## アクセスリストの追加・削除

何も設定されていない状態で以下のようなパラメータをモジュールに入力すると、

```yaml
acl_cli:
  - permit ip 192.168.10.0 0.0.0.255 any
  - permit ip 192.168.20.0 0.0.0.255 any
  - permit ip 192.168.30.0 0.0.0.255 any
  - permit ip 192.168.40.0 0.0.0.255 any
  - permit ip 192.168.50.0 0.0.0.255 any
```

以下の出力を得ます。

```json
"commands": [
    "10 permit ip 192.168.10.0 0.0.0.255 any",
    "20 permit ip 192.168.20.0 0.0.0.255 any",
    "30 permit ip 192.168.30.0 0.0.0.255 any",
    "40 permit ip 192.168.40.0 0.0.0.255 any",
    "50 permit ip 192.168.50.0 0.0.0.255 any"
]
```

この設定がなされた状態で、今度は1行目と2行目を入れ替えた以下のような入力パラメータをモジュールに入力すると、

```yaml
acl_cli:
  - permit ip 192.168.20.0 0.0.0.255 any
  - permit ip 192.168.10.0 0.0.0.255 any
  - permit ip 192.168.30.0 0.0.0.255 any
  - permit ip 192.168.40.0 0.0.0.255 any
  - permit ip 192.168.50.0 0.0.0.255 any
```

以下の出力を得ます。

```json
"commands": [
    "no 10 permit ip 192.168.10.0 0.0.0.255 any",
    "no 20 permit ip 192.168.20.0 0.0.0.255 any",
    "10 permit ip 192.168.20.0 0.0.0.255 any",
    "20 permit ip 192.168.10.0 0.0.0.255 any"
]
```

## プレイブックの例

```yaml
---

- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  tasks:

    #
    # TEST 1
    #

    - name: create config to be pushed
      iida.local.ios_ip_acl:
        show_access_list: ""
        acl_cli: "{{ acl_cli }}"
        debug: true
      register: r
      vars:
        acl_cli:
          - permit ip 192.168.10.0 0.0.0.255 any
          - permit ip 192.168.20.0 0.0.0.255 any
          - permit ip 192.168.30.0 0.0.0.255 any
          - permit ip 192.168.40.0 0.0.0.255 any
          - permit ip 192.168.50.0 0.0.0.255 any

    - name: TEST 1
      debug:
        var: r

    #
    # TEST 2
    #

    - name: create config to be pushed
      iida.local.ios_ip_acl:
        show_access_list: "{{ show_access_list }}"
        acl_cli: "{{ acl_cli }}"
        debug: true
      register: r
      vars:
        # show access-lists {{ acl_name }} | include ^ +[1-9]
        show_access_list: |
          10 permit ip 192.168.10.0 0.0.0.255 any
          20 permit ip 192.168.20.0 0.0.0.255 any
          30 permit ip 192.168.30.0 0.0.0.255 any
          40 permit ip 192.168.40.0 0.0.0.255 any
          50 permit ip 192.168.50.0 0.0.0.255 any

        acl_cli:
          - permit ip 192.168.20.0 0.0.0.255 any
          - permit ip 192.168.10.0 0.0.0.255 any
          - permit ip 192.168.30.0 0.0.0.255 any
          - permit ip 192.168.40.0 0.0.0.255 any
          - permit ip 192.168.50.0 0.0.0.255 any



    - name: TEST 2
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
            "10 permit ip 192.168.10.0 0.0.0.255 any",
            "20 permit ip 192.168.20.0 0.0.0.255 any",
            "30 permit ip 192.168.30.0 0.0.0.255 any",
            "40 permit ip 192.168.40.0 0.0.0.255 any",
            "50 permit ip 192.168.50.0 0.0.0.255 any"
        ],
        "failed": false
    }
}

TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "no 10 permit ip 192.168.10.0 0.0.0.255 any",
            "no 20 permit ip 192.168.20.0 0.0.0.255 any",
            "10 permit ip 192.168.20.0 0.0.0.255 any",
            "20 permit ip 192.168.10.0 0.0.0.255 any"
        ],
        "failed": false
    }
}
```
