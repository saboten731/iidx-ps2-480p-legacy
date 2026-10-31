# beatmania IIDX（PS2）— 480pパッチ

[English](README.md) | **日本語**

PlayStation 2版『beatmania IIDX 3rd〜8th style』を、PS2実機から**480pで映像出力**する非公式パッチです。

ゲーム本来の描画解像度を維持しつつ、映像出力と表示位置を調整します。**6作品すべてについて、PS2実機で映像・音声・演奏動作を確認済みです。**

> **画質について：** 480pで出力しますが、ゲーム自体をネイティブ640×480で描き直すものではありません。元の映像を縦方向に拡大してプログレッシブ出力します。9th style以降のネイティブ480pパッチとは方式が異なります。

## 対応ソフト

**最新更新：[v1.21](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.21)**。各作品のパッチは下の表からダウンロードしてください。

| 作品 | 配布パッチ | リリース |
|---|---|---|
| **3rd style** | [`IIDX03_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX03_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **4th style** | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX04_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **5th style** | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX05_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **6th style** | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.21/IIDX06_480p.xdelta) | [v1.21](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.21) |
| **7th style** | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX07_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |
| **8th style** | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX08_480p.xdelta) | [v1.2](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.2) |

過去のリリースも履歴として公開しています。**未改変ISOにパッチを1種類だけ**適用し、重ね掛けはしないでください。

## 適用方法

お持ちのゲームディスクから作成したISOを用意してください。適用方法は**xdelta**と**Python**の2種類で、どちらか一方を使います。

### 方法1：xdelta（推奨）

1. 上の表から該当作品の`.xdelta`をダウンロードします。
2. 未改変ISOのSHA-256を、[checksums.txt](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.21/checksums.txt)に記載された**基準ISO**と照合します。
3. Delta Patcherまたは[xdelta3](https://github.com/jmacd/xdelta/releases)でパッチを適用します。
4. 必要に応じて、適用後ISOのSHA-256を同じchecksumsの**適用後ISO**と照合してください。

xdeltaは**指定された基準ISO専用**です。元ISOのハッシュが異なる場合は無理に適用せず、下記のPython版を検討してください。

使用例（パスとパッチ名は適宜変更）：

```sh
xdelta3 -d -s "<元ISO>" "IIDX05_480p.xdelta" "<出力ISO>"
```

### 方法2：Python

[`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py)を使用します。**Python 3.10以降**が必要です。追加ライブラリは不要です。

```sh
python patch480p.py "<元ISO>"
```

元ISOは変更せず、別のISOを生成します。出力先は`--output`で指定できます。

Python版では対応する元ゲームデータを照合し、未対応またはパッチ適用済みのISOは受け付けません。所有するゲームディスクから作成した未改変ISOを使用してください。

## PS2実機で使うとき

- **480p対応のテレビ・モニター**と480pを伝送できる接続環境が必要です。
- **GSMの映像モード強制設定はOFF**にしてください。パッチ側で480pを設定します。
- 色出力はPS2本体の**RGB／コンポーネント設定**に従います。接続ケーブルの自動判別ではありません。**RGB接続での実機動作は未確認**です。

## 実機動作確認

### 検証環境

| ID | PS2型番 | 起動方法 / ストレージ | 映像接続 | 表示機器 | GSM |
|---|---|---|---|---|---|
| A | SCPH-77000（日本版） | OPL（MX4SIO／USB） | D端子（コンポーネント） | 480p対応テレビ（直結・スケーラーなし） | OFF |

### 実機動作確認

| 環境 | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**凡例：** ✓ = 記載環境で映像・音声・演奏動作を確認 / — = 未検証

**5th style** では、v1.1で480p出力時に発生していた音声再生不具合に対し、v1.2で`IOP_MAIN.IRX`のHLINEタイマー間隔2か所を補正しました。実機確認では左右の音声が正常に再生され、蓄積する音ズレも確認されませんでした。

ほかのPS2型番・表示機器・起動方法での動作は未確認です。また、全楽曲や長時間動作を網羅した検証ではありません。

## 補足

- **ISO・ゲーム実行ファイル・ゲーム素材は配布していません。** お持ちのゲームディスクから作成したISOをご利用ください。
- 映像出力と表示タイミングを調整します。**5th styleのみ480p時の正常な音声再生のためIOP音声タイマーも補正**します。楽曲素材・譜面・判定データを意図的に変更するものではありません。
- 元ISOは保管し、適用後ISOを別途1本作れる空き容量を確保してください。
- checksumsに掲載する適用後ISOのSHA-256は**基準ISOに適用した場合**の値です。Python版で基準と異なるISOを処理した場合、出力ハッシュも異なることがあります。

## 謝辞

配布方法の構成は [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p) を参考にしました。本プロジェクトは3rd〜8th styleを対象とした別実装です。

## ライセンス・免責事項

パッチプログラムと本プロジェクトのドキュメントは[MIT License](LICENSE)で公開しています。ゲーム本体・素材・商標の権利は各権利者に帰属します。

本パッチは非公式であり、KONAMIから承認・支援を受けていません。
