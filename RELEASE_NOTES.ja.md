# beatmania IIDX 3rd style — 480pパッチ v1.0

PlayStation 2版『beatmania IIDX 3rd style』向け480pパッチの初回リリースです。

### 主な変更点

- ゲーム本来の240行の画面を縦方向に2倍し、**480pで映像出力**します。
- 表示位置と映像の同期を調整し、**PS2実機で音楽・譜面のズレが生じないことを確認**しました。
- PS2本体のRGB／コンポーネント設定に合わせて色出力を切り替えます。

※ ゲームの描画そのものをネイティブ640×480に変更するものではありません。

### ダウンロードと適用

| ファイル | 用途 |
|---|---|
| [`IIDX03_480p_v1.0.xdelta`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/IIDX03_480p_v1.0.xdelta) | 基準ISO用パッチ。通常はこちらを使用してください。 |
| [`checksums.txt`](https://github.com/saboten731/iidx-ps2-480p-legacy/releases/download/v1.0/checksums.txt) | 元ISOと適用後ISOの確認用ハッシュ。 |

元ISOのハッシュが異なる場合は、[リポジトリの `patch480p.py`](https://github.com/saboten731/iidx-ps2-480p-legacy) も利用できます（対応する未改変のゲーム実行ファイルが必要です）。

### 動作確認・注意事項

PS2実機で、タイトル画面・HOW TO PLAY・選曲・演奏・打鍵判定・長時間動作を確認済みです。確認環境はOPL／MX4SIO、D端子接続、**GSM OFF**。RGB接続での実機動作は未確認です。

**対応は3rd styleのみ**です。4th〜8th styleは現時点では未対応です。

パッチ適用方法と動作条件は [日本語README](https://github.com/saboten731/iidx-ps2-480p-legacy/blob/main/README.ja.md) を参照してください。**ゲーム本体やISOは含まれません。** 本パッチは非公式であり、KONAMIから承認・支援を受けていません。
