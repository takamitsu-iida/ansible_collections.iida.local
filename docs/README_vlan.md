# CatalystのVLAN設定を生成するローカルモジュール

**iida.local.ios_vlan** はCatalystのVLAN設定コマンドを生成します。

> **ローカルモジュールとは**
>
> 事前に採取しておいたコンフィグおよび希望する状態を入力すると、その状態にするための設定コマンドを出力するモジュールです。
> 対象装置への接続は必要ありません。
> 事前に投入するコマンドをレビューしたい場合に便利です。

<br>

## モジュールへの入力

- **running_config** 既存設定(show running-config vlan)を文字列として指定します
- **running_config_path** 既存設定(show running-config vlan)を保存したファイルへのパスを指定します

<br>

### 希望する設定を指定するパラメータ

- **vlans** 希望するVLANの状態をYAML形式（リスト）で指定します

<br>

### VLAN設定パラメータ

- **vlan_id** VLAN IDを数字で指定
- **vlan_name** VLANモード内のnameコマンドに指定する文字列
- **vlan_range** 複数のVLANを'-'と','で指定します
- **state** VLANの状態presentもしくはabsentで指定します

<br>

## モジュールからの出力

- **commands** 流し込むべきコマンドをリストにしたもの

<br>

## VLANの追加と削除

1-4094まで全てのVLANについて、presentかabsentで表現しておくとよいと思います。
連続したVLANは'-'で連結します。連続しない場合は','で連結します。

```yaml
vlans:
  - vlan_id: 2
    vlan_name: inside
    state: present

  - vlan_id: 3
    vlan_name: outside
    state: present

  - vlan_range: 4-9
    state: present

  - vlan_range: 10-4094
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
      Building configuration...

      Current configuration:
      !
      vlan 2
       name -inside-
      !
      vlan 3
       name -outside-
      !
      vlan 4,6,8
      end


  tasks:

    # - include_vars: vars/c3560g.yml

    #
    # TEST 1
    #
    - name: create config to be pushed
      iida.local.ios_vlan:
        running_config: "{{ running_config }}"
        vlans: "{{ vlans }}"
      register: r

      vars:
        vlans:
          # 1-4094すべてのVLAN情報をpresent/absentで表現した方がいい
          - vlan_id: 2
            vlan_name: inside
            state: present

          - vlan_id: 3
            vlan_name: outside
            state: present

          - vlan_range: 4-9
            state: present

          - vlan_range: 10-4094
            state: absent


    - name: TEST 1
      debug:
        var: r

    #
    # TEST 2
    #
    - name: create config to be pushed
      iida.local.ios_vlan:
        running_config: "{{ running_config }}"
        vlans: "{{ vlans }}"
      register: r

      vars:
        vlans:
          - vlan_id: 2
            vlan_name: inside
            state: present

          - vlan_id: 3
            vlan_name: outside
            state: present

          - vlan_range: 4
            state: absent

          - vlan_range: 5
            state: present

          - vlan_range: 6-4094
            state: absent

    - name: TEST 2
      debug:
        var: r
```

<br>

## 実行結果

```bash
TASK [TEST 1]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "vlan 5,7,9",
            "exit",
            "vlan 2",
            "name inside",
            "exit",
            "vlan 3",
            "name outside",
            "exit"
        ],
        "failed": false
    }
}

TASK [TEST 2]
ok: [localhost] => {
    "r": {
        "changed": false,
        "commands": [
            "vlan 5",
            "exit",
            "no vlan 4,6,8",
            "vlan 2",
            "name inside",
            "exit",
            "vlan 3",
            "name outside",
            "exit"
        ],
        "failed": false
    }
}
```
