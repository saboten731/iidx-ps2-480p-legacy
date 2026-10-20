# IIDX 3rd Style 480p Patch v1.0

v1.0は、PlayStation 2版『beatmania IIDX 3rd Style』（製品番号 `SLPM_650.06`）向けの実機検証済み480pパッチです。GSの表示回路で既存の240行画像を垂直2倍して出力します。ネイティブ640×480描画へ変更するものではありません。

## パッチ内容

- `patch480p.py`: BOOT2 ELFを検証し、別ISOへ書き出すPython 3パッチャー。
- `IIDX03_SLPM-65006_480p_v1.0.xdelta`: 検証済み基準ISO用のxdelta3パッチです。[GitHub Releasesページ](https://github.com/saboten731/iidx-ps2-480p-legacy/releases)のv1.0 Release添付から入手してください。
- `checksums.txt`: 基準ISO、出力ISO、xdelta、Pythonパッチ出力のSHA-256。

ISO、ELF、BIOS、IRX、ゲーム素材は含みません。xdeltaは `checksums.txt` 記載のSHA-256に一致する基準ISOだけに適用してください。

## パッチの詳細

- 描画: `DISPLAY=0x001DF4FF0882B138`（240行を縦2倍し、480出力ライン）。
- 映像同期: `SYNCV=0x00C7900001E00006`（`VDP=484`）。
- BIOS/OSDに基づく実行時の色選択と、ゲーム本来のPMODE復旧経路を維持します。
- 音声ピッチ、譜面タイマー、判定処理への補正は追加していません。

## 対応と検証

- v1.0の対応は3rd Style `SLPM_650.06` のみです。4th〜8th Styleは今後個別に解析・検証する予定で、このリリースには含まれず未対応です。
- Pythonパッチャーは対応する未改変BOOT2 ELFだけを受け付け、元ISOを変更せず新しいISOを作成します。
- ユーザー報告による実機確認環境は、PS2実機、OPL、MX4SIO、コンポーネント入力テレビ直結、GSM OFFです。タイトル、HOW TO PLAY、選曲、プレイ、打鍵判定、長時間動作が確認されています。この結果は同構成に対するものです。
- 適用手順、対応ハッシュ、制約は `README.ja.md`、`README.md`、`checksums.txt` を参照してください。

## ライセンスと表記

プロジェクトのオリジナルソースコードとドキュメントはMIT Licenseで公開しています。全文は `LICENSE` を参照してください。ゲームデータは含みません。本パッチは非公式ファンパッチであり、Konamiの承認または支援を受けていません。
