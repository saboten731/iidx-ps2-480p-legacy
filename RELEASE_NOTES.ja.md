# IIDX 3rd Style 480p Patch v1.0（下書き）

PlayStation 2版『beatmania IIDX 3rd Style』製品番号 `SLPM_650.06` 向けのv1.0パッチです。

## 変更内容

- ゲーム本来の240行画像を垂直方向に2倍して480p出力します。ネイティブ640×480描画への変更ではありません。
- `DISPLAY=0x001DF4FF0882B138` と、検証済みの映像同期設定 `SYNCV=0x00C7900001E00006`（`VDP=484`）を使用します。
- BIOS/OSDに基づく色選択と、ゲーム本来のPMODE復旧経路を維持します。
- 音声、譜面タイマー、判定処理への補正は追加していません。

## 対応と検証

- 対応タイトルは3rd Style `SLPM_650.06` のみです。このリリースでは他Styleは未対応です。
- xdeltaは `checksums.txt` 記載の検証済み基準ISO専用です。
- Pythonパッチャーは許可リストに一致する未改変BOOT2 ELFのみ受け付け、別ファイルにISOを出力します。
- ユーザー報告による実機確認環境は、PS2実機、OPL、MX4SIO、コンポーネント入力テレビ直結、GSM OFFです。タイトル、HOW TO PLAY、選曲、プレイ、判定、長時間動作が確認されています。
- ISO、ELF、BIOS、IRXなどのゲームデータは含みません。

適用方法、制約、ハッシュは `README.ja.md`、`README.md`、`checksums.txt` を参照してください。

## 下書き状態

プロジェクトのソースライセンスは未選定です。ライセンス、日英Release Notes、README、添付xdeltaのハッシュを確認するまで、このReleaseは下書き状態にします。本作は非公式ファンプロジェクトであり、Konamiの承認を受けていません。
