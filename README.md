# Ansible Collection - iida.local

Ansible Collection to generate config diff

## Requirements

- Ansible 2.9 or later

## Install/Uninstall

1. Clone this repository

```bash
git clone https://github.com/takamitsu-iida/ansible_collections.iida.local.git
```

1. Build collection

```bash
make build
```

1. Install collection to your personal environment

The collection will be installed to ~/.ansible/collections/ansible_collections/

```bash
make install
```

---

# Ansibleローカルモジュール

ネットワーク機器の設定をAnsibleで変更するためのモジュールです。

<br>

## ローカルモジュールとは

Ansibleのコアモジュールはいずれも以下の動作を一つのモジュールの中で完結してしまいます。

- リモートデバイスから情報を収集
- 差分コンフィグを生成
- リモートデバイスに適用

<br>

これらの機能うち差分コンフィグを生成する機能だけを使いたくても、できない作りになっています。

そこで事前に採取しておいたリモートデバイスの設定情報と希望するコンフィグ状態を入力すると、打ち込むべきコマンドを生成するモジュールを作成しました。
リモートデバイスへの接続を行わないので、ここではローカルモジュールと呼んでいます。

<br>

SSHで接続できないネットワークデバイスに対して冪等性のある設定変更を行いたい場合、ローカルモジュールが便利でしょう。

## プレイブックの例

事前に採取済みの情報を使って差分コマンドを生成するなら、localhostをターゲットに実行します。
簡単なものであれば以下のようにvarsにパラメータを直書きしてもいいでしょう。

```yaml
- name: playbook for module test
  hosts: localhost
  connection: local
  gather_facts: false

  tasks:

    - name: create config to be pushed
      iida.local.ios_interface:
        running_config: "{{ running_config }}"
        interfaces: "{{ interfaces }}"
        debug: true
      register: r
      vars:
        running_config: |
        !
        interface GigabitEthernet3
         description configured by hand
        !

        interfaces:
          - name: GigabitEthernet3
            description: configured by ansible
            state: present

    - name: TEST 1
      debug:
        var: r
```

稼働中の装置から(ios_commandモジュール等を使って)情報を採取する場合、
プレイブックのhostsはその装置になります。
ローカルモジュールに対しては`delegate_to: localhost`をつけてください。

<br>

# 設定パラメータの考え方

Cisco IOSのコマンドラインは以下の特徴を持っています。

- デフォルトの設定は表示されない
- 設定を消すにはnoを付ける(消されると設定は表示されなくなる)

一方、Ansibleの文化では以下の動作をします。

- state: presentはその状態であることが正
- state: absentはその状態が存在しないことが正

あるパラメータはデフォルトの状態が正、別のパラメータは変更が必要、
というのをAnsibleの流儀に従ってstateだけでやろうとすると、タスクを分離しなければいけません。

ローカルモジュールではできるだけpresentだけで状態を表現するようにしています。

例えばインタフェースのパラメータとしてdescriptionとmtuとspeedを設定したとします。

```yaml
- name: GigabitEthernet3
  description: configured by ansible
  speed: 1000
  mtu: 1512
  state: present
```

mtuの設定をデフォルト状態に戻したいときには、以下のようにmtuの値だけを空白にします。

```yaml
- name: GigabitEthernet3
  description: configured by ansible
  speed: 1000
  mtu:
  state: present
```

ローカルモジュールはmtuの設定をデフォルト状態に戻すために以下のコマンドを生成します。

```bash
interface GigabitEthernet3
no mtu
```

stateをabsentにするのは、対象物をまるまる消したい場合に使います。
たとえば論理インタフェースLoopback0を削除したいのであれば、以下のように指定します。

```yaml
- name: Loopback0
  state: absent
```

<br>

# Cisco IOS系ローカルモジュール

Cisco IOSルータを対象にしたローカルモジュールです。

<br>

## iida.local.ios_interface

[説明　README_interface.md](docs/README_interface.md)

[プレイブック](playbooks/interface.yml)

インタフェース内のパラメータを設定するローカルモジュールです。

現在は以下のパラメータを設定できます。
不足するパラメータは必要に応じてモジュールを改造すればいいでしょう。

- description
- negotiation
- speed
- duplex
- mtu
- shutdown

<br>

## iida.local.ios_interface_address

[説明　README_interface_address.md](docs/README_interface_address.md)

[プレイブック](playbooks/interface_address.yml)

インタフェースにIPアドレスを設定するローカルモジュールです。
セカンダリアドレスにも対応しています。

IPv6アドレスも設定できるようにしたつもりですが、普段IPv6を使っていないので正しく機能するかわかりません・・・

<br>

## iida.local.ios_hsrp

[説明　README_hsrp.md](docs/README_hsrp.md)

[プレイブック](playbooks/hsrp.yml)

HSRPの設定コマンドを生成するローカルモジュールです。

<br>

## iida.local.ios_static_route

[説明　README_static_route.md](docs/README_static_route.md)

[プレイブック](playbooks/static_route.yml)

スティックルートの設定を生成するローカルモジュールです。
スタティックルートが大量にある場合に便利です。

<br>

## iida.local.ios_ip_acl

[説明　README_ip_acl.md](docs/README_ip_acl.md)

[プレイブック](playbooks/ip_access_list.yml)

ip access-listの中身を管理します。
順番の入れ替えや追加、削除といった操作はどうしても間違えがちなので、このモジュールで差分コンフィグを生成した方が安全でしょう。

<br>

# Cisco Catalyst系ローカルモジュール

IOS Catalystを対象にしたローカルモジュールです。

<br>

## iida.local.ios_vlan

[説明　README_vlan.md](docs/README_vlan.md)

[プレイブック](playbooks/vlan.yml)

VANの定義は','や'-'を使った変則的なコマンド入力になりますのでどうしても間違えやすいです。
このモジュールで差分コンフィグを生成した方が安全でしょう。

<br>

## iida.local.ios_interface_trunk

[説明　README_interface_trunk.md](README_interface_trunk.md)

[プレイブック](playbooks/interface_trunk.yml)

インタフェースにVLANを通す、通さない、といった設定変更は間違えやすいものの一つです。
このモジュールで差分コンフィグを生成した方が安全でしょう。

<br>

## iida.local.ios_linkagg

[説明　README_linkagg.md](docs/README_linkagg.md)

[プレイブック](playbooks/linkagg.yml)

リンクアグリゲーションの設定は複数の物理インタフェースに設定することになりますので、手作業で変更すると間違えやすいです。
このモジュールで差分コンフィグを生成した方が安全でしょう。

<br>

# IOSデバイスへのコンフィグの流し込み

ローカルモジュールで生成した差分コンフィグをリモートデバイスに流し込むには、独自に作成した`ios_cfg`モジュールを使います。

ios_configモジュールは親子関係を指定する必要があるため少々使いづらく、しばしば期待通りになりません。
できるだけ`ios_cfg`モジュールを使って流し込みましょう。

## 使い方

```yaml
- name: apply config to the remote device
  iida.local.ios_cfg:
    lines: "{{ commands }}"
  when:
    - commands
  register: r
```
