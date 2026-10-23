# beatmania IIDX（PS2）— 480pパッチ

[English](README.md) | **日本語**

PlayStation 2版『beatmania IIDX 3rd〜8th style』を、PS2実機から**480pで映像出力**する非公式パッチです。

ゲーム本来の描画解像度を維持しながら、映像の出力方式と表示位置を調整します。**対応する6作品すべてで、PS2実機による画面表示と演奏動作を確認済み**です。

> **画質について：** 480pで出力しますが、ゲーム自体をネイティブ640×480で描き直すものではありません。元の映像を縦方向に拡大してプログレッシブ出力します。9th style以降のネイティブ480pパッチとは方式が異なります。

## 対応ソフト

| 作品 | 配布パッチ | リリース |
|---|---|---|
| **3rd style** | [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) | [v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0) |
| **4th style** | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX04_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **5th style** | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX05_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **6th style** | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX06_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **7th style** | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX07_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |
| **8th style** | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX08_480p.xdelta) | [v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1) |

**3rd style** は公開済みの **v1.0** を引き続き利用します。**v1.1** で **4th〜8th style** を追加しました。1作品のパッチ適用に両方のリリースをダウンロードする必要はありません。

## 適用方法

お持ちのゲームディスクから作成したISOを用意してください。適用方法は**xdelta**と**Python**の2種類です。どちらか一方を使用します。

### 方法1：xdelta（推奨）

1. 上の表から、お使いの作品に対応する `.xdelta` をダウンロードします。
2. 元ISOのSHA-256が、該当作品の**基準ISO**の値と一致することを確認します：[v1.0のchecksums（3rd）](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt)／[v1.1のchecksums（4th〜8th）](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/checksums.txt)。
3. Delta Patcherや [xdelta3](https://github.com/jmacd/xdelta/releases) などでパッチを適用します。
4. 必要に応じて、適用後ISOのSHA-256をchecksumsの**適用後ISO**の値と照合してください。

xdeltaは**指定された基準ISO専用**です。元ISOのハッシュが異なる場合は無理に適用せず、下記のPython版を検討してください。

コマンドラインでの使用例（xdelta3。山括弧の部分はご自身のパスに置き換えてください）：

```sh
xdelta3 -d -s "<元ISO>" "IIDX04_480p.xdelta" "<出力ISO>"
```

### 方法2：Python（元ISOのハッシュが異なる場合）

リポジトリの [`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) を使用します。**Python 3.10以降**が必要です。追加ライブラリは不要です。

```sh
python patch480p.py "<元ISO>"
```

元ISOは変更せず、別のISOを作成します。出力先を指定する場合は `--output` を使用してください。

Python版はISO全体のハッシュが異なっていても、**ゲームの実行ファイルが対応済みの未改変版と完全一致する場合**には適用できます。別バージョンや改造済みの実行ファイル、パッチ適用済みのISOは受け付けません。すべての再構成ISOでの動作を保証するものではありません。

## PS2実機で使うとき

- **480p対応のテレビ・モニター**と、480pを伝送できる接続環境が必要です。
- **GSMによる映像モードの強制設定はOFF**にしてください。パッチ側で480p出力を設定します。
- 色出力はPS2本体の**RGB／コンポーネント設定**に従います。接続ケーブルを自動判別するものではありません。**RGB接続での実機動作は未確認**です。

## 実機動作確認

### 検証環境

| ID | PS2型番 | 起動方法 / ストレージ | 映像接続 | 表示機器 | GSM |
|---|---|---|---|---|---|
| A | SCPH-77000（日本版） | OPL / MX4SIO | D端子（コンポーネント） | 480p対応テレビ（直接接続・スケーラーなし） | OFF |

### 作品別動作結果

| 環境 | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| A | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**凡例：** ✓ = 動作確認済み / ✗ = 不具合確認 / — = 未検証

✓ は記載された環境で映像表示と演奏動作を確認したことを示します。ほかのPS2型番・映像接続・表示機器・起動方法での動作は未確認です。すべての楽曲や長時間動作を網羅した検証ではありません。

## 補足

- **ISOやゲーム本体・ゲーム素材は配布していません。** お持ちのゲームディスクから作成したISOをご利用ください。
- 変更対象は映像出力であり、楽曲データ・譜面・判定処理には手を加えていません。
- 元ISOは保管し、新たにISOを1本作れる空き容量を確保してください。
- checksumsに掲載された適用後ISOのSHA-256は、**基準ISOに適用した場合**の値です。Python版で基準と異なるISOを処理した場合、適用後のハッシュも異なることがあります。

## 謝辞

配布方法の構成は [blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p) を参考にしました。本プロジェクトは3rd〜8th styleを対象とした別実装です。

## ライセンス・免責事項

パッチプログラムと本プロジェクトのドキュメントは [MIT License](LICENSE) で公開しています。ゲーム本体・素材・商標の権利は各権利者に帰属します。

本パッチは非公式であり、KONAMIから承認・支援を受けていません。
