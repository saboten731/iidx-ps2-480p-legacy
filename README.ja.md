# beatmania IIDX 3rd style — 480pパッチ

[English](README.md) | **日本語**

PlayStation 2版『beatmania IIDX 3rd style』を、PS2実機から**480pで映像出力**する非公式パッチです。

ゲーム本来の240行の画面を縦方向に2倍して出力し、480p化に伴う画面表示や音楽との同期も調整しています。**選曲から実際の演奏まで、PS2実機で動作確認済み**です。

> **画質について：** 出力は480pになりますが、ゲームの描画そのものを640×480に高精細化するパッチではありません。9th style以降を対象としたネイティブ480pパッチとは方式が異なります。

## 対応ソフト

- **beatmania IIDX 3rd style（PS2版）** — v1.0対応・実機確認済み
- **4th〜8th style** — 現時点では未対応。各作品の検証が完了したものから追加予定です。

## 適用方法

ご自身で所有するディスクから作成したISOを用意してください。適用方法は**xdelta**と**Python**の2種類です。どちらか一方を使用します。

### 方法1：xdelta（推奨）

1. [Releases](https://github.com/saboten731/iidx-ps2-480p-legacy/releases)から [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) をダウンロードします。
2. 元ISOのSHA-256が、配布されている [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt) の**基準ISO**と一致することを確認します。
3. Delta Patcherなどのxdelta対応ツールで、元ISOにパッチを適用します。

xdeltaは**指定された基準ISO専用**です。ハッシュが異なるISOには使用せず、下記のPython版を試してください。

コマンドラインで適用する場合（xdelta3）：

```sh
xdelta3 -d -s "beatmania IIDX 3rd style.iso" "IIDX03_480p_v1.0.xdelta" "beatmania IIDX 3rd style_480p.iso"
```

※ ISOのファイル名は一例です。手元のファイル名に読み替えてください。

### 方法2：Python（ISOのハッシュが異なる場合）

[リポジトリ](https://github.com/saboten731/iidx-ps2-480p-legacy)の `patch480p.py` とPython 3.8以降を使用します。追加ライブラリは不要です。

```sh
python patch480p.py "beatmania IIDX 3rd style.iso"
```

元ISOは書き換えず、末尾に `_480p_v1.0` を付けた新しいISOを作成します。出力先を指定したい場合は `--output` を使用できます。

Python版はISO全体のハッシュが異なっていても、**ゲームの実行ファイルが対応済みの未改変版と一致する場合**に適用できます。別バージョンや改造済みの実行ファイルには適用しません。あらゆるISOでの動作を保証するものではありません。

## PS2実機で使うとき

- **480pに対応したテレビやモニター**と、480pを伝送できる接続環境が必要です。実機確認にはコンポーネント（D端子）接続を使用しました。
- **GSMによる映像モードの強制設定はOFF**にしてください。パッチがゲーム側で480p出力を設定します。
- 色出力はPS2本体の**RGB／コンポーネント設定**に従います。ケーブルの種類を自動検出する機能ではありません。RGB接続での実機動作は未確認です。

動作確認環境は、PS2実機・OPL・MX4SIO・D端子接続のテレビ（GSM OFF）です。タイトル、HOW TO PLAY、選曲、演奏、打鍵判定、長時間動作を確認しました。ほかの接続機器や起動方法では結果が異なる場合があります。

## 補足

- **ISOやゲームデータは配布していません。** パッチの利用には、ご自身で用意したゲームのISOが必要です。
- 映像出力を変更するパッチであり、音声データや譜面、判定処理には手を加えていません。
- 新しいISOを作成するため、元ISOと同程度の空き容量が必要です。元ISOは保管し、生成されたISOの確認には配布物の `checksums.txt` を利用してください。基準ISO以外から生成した場合、完成ISOのハッシュは掲載値と一致しないことがあります。

## 謝辞

配布方法の構成は、[blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p) を参考にしました。本パッチは3rd style向けの別実装です。

## ライセンス・免責事項

パッチプログラムと本プロジェクトのドキュメントは [MIT License](LICENSE) で公開しています。ゲーム本体およびその素材・商標の権利は各権利者に帰属します。

本パッチは非公式のもので、KONAMIから承認・支援を受けていません。
