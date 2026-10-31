# beatmania IIDX（PS2）— 480pパッチ 更新履歴

[English](RELEASE_NOTES.md) | **日本語**

## v1.21

- **6th style**の基準ISOを[Redump登録データ](https://redump.info/disc/35599/)と一致するものに修正し、xdeltaとPython版パッチャーを更新しました。
- PS2実機で480p映像・音声・演奏動作を確認済みです。他作品のパッチに変更はありません。

[v1.21をダウンロード](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.21)

---

## v1.2

PS2版『beatmania IIDX 3rd〜8th style』の**6作品すべて**について、共通のBIOS-native 480p方式へ更新しました。**全作品でPS2実機による映像・音声・演奏動作を確認済み**です。

### 主な変更点

- **3rd〜8th style** を共通のBIOS-native 480p出力方式へ更新し、作品ごとの表示調整を反映しました。
- **5th styleの480p時の音声再生不具合を修正しました。** v1.1では左右で異なるBGMが鳴る、メニューSEが正しく再生されない等の問題がありました。v1.2では`IOP_MAIN.IRX`のHLINEタイマー間隔2か所を補正し、実機で左右の正常な音声再生と音ズレのない演奏を確認しました。
- ゲーム本来の描画解像度は維持します。**480p出力であり、ネイティブ640×480描画ではありません。**

**5th styleをご利用の方へ：** 旧v1.1のxdeltaには、検証環境で確認された音声不具合があります。**未改変ISOにv1.2を適用**してください。旧パッチを重ねて適用しないでください。

### ダウンロード

| 作品 | パッチ |
|---|---|
| 3rd style | [`IIDX03_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX03_480p.xdelta) |
| 4th style | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX04_480p.xdelta) |
| 5th style | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX05_480p.xdelta) |
| 6th style | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX06_480p.xdelta) |
| 7th style | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX07_480p.xdelta) |
| 8th style | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/IIDX08_480p.xdelta) |

元ISO・適用後ISO・xdeltaのSHA-256は[`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.2/checksums.txt)で確認できます。xdeltaは**一致する基準ISO専用**です。元ISO全体のハッシュが異なる場合は、対応する未改変実行ファイルを対象とする[`patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py)も利用できます。**5th styleでは未改変`IOP_MAIN.IRX`の一致も必要**です。手順は[日本語README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.ja.md)を参照してください。ISOやゲームデータは配布していません。

### 実機検証・注意事項

日本版SCPH-77000、OPL（MX4SIO／USB）、D端子（コンポーネント）直結、**GSM OFF**で全6作品の映像・音声・演奏動作を確認しました。**RGB接続は実機未検証**です。その他のPS2型番、起動環境、全楽曲・長時間動作を網羅した検証ではありません。

過去の[v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0)・[v1.1](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.1)は履歴として残しています。

本パッチは非公式であり、KONAMIから承認・支援を受けていません。ゲーム本体・素材・商標の権利は各権利者に帰属します。
