# beatmania IIDX（PS2）— 480pパッチ v1.1

[English](RELEASE_NOTES.md) | **日本語**

PS2版『beatmania IIDX』の480pパッチを、従来の**3rd styleから3rd〜8th styleの6作品**へ拡張しました。今回新たに追加した**4th・5th・6th・7th・8th style**は、すべてPS2実機で動作確認済みです。

### 主な変更点

- **4th〜8th style** の480p出力に対応しました。
- 作品ごとに映像の出力方式と表示位置を調整し、実機で画面表示と演奏動作を確認しました。
- ゲーム本来の描画解像度は維持します。**480p出力であり、ネイティブ640×480描画ではありません。**
- **3rd styleに変更はありません。** 引き続き [v1.0](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/tag/v1.0) から入手できます。

### ダウンロード

| 作品 | パッチ |
|---|---|
| 4th style | [`IIDX04_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX04_480p.xdelta) |
| 5th style | [`IIDX05_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX05_480p.xdelta) |
| 6th style | [`IIDX06_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX06_480p.xdelta) |
| 7th style | [`IIDX07_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX07_480p.xdelta) |
| 8th style | [`IIDX08_480p.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/IIDX08_480p.xdelta) |

元ISOのハッシュ・適用後ISOのハッシュ・配布パッチのハッシュは [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.1/checksums.txt) で確認できます。xdeltaは**ハッシュが一致する基準ISO専用**です。ISOやゲームデータは配布していません。

元ISOのハッシュが異なっていても、対応する未改変のゲーム実行ファイルが一致する場合は、[リポジトリの `patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/patch480p.py) を利用できます。適用方法は [日本語README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.ja.md) を参照してください。

### 実機検証・注意事項

追加した5作品は、PS2実機・OPL／MX4SIO・D端子（コンポーネント）接続・**GSM OFF**で、映像表示と演奏動作を確認しました。ほかの接続環境や起動方法では動作が異なる場合があります。**RGB接続は実機未検証**であり、すべての楽曲や長時間動作を全作品で網羅したものではありません。

本パッチは非公式であり、KONAMIから承認・支援を受けていません。ゲーム本体・素材・商標の権利は各権利者に帰属します。
