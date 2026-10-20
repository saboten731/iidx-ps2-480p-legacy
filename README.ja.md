# beatmania IIDX 3rd Style 480p patch v1.0

PS2版『beatmania IIDX 3rd Style』（製品番号 `SLPM_650.06`）向けの非公式ファンパッチです。v1.0ではゲーム本来の240行描画を垂直2倍して480pで出力します。後述の構成でPS2実機の動作確認済みです。

## 対応状況

- **3rd Style v1.0:** 本リポジトリで提供・サポートする唯一のパッチです。後述の[実機確認条件](#実機確認条件)で検証済みです。
- **4th〜8th Style:** 各タイトルを個別に解析・検証したうえで、将来追加を検討します。現時点でパッチは含まれておらず、v1.0では未対応です。

この方式はゲームをネイティブ640×480描画へ変更するものではありません。3rd Styleの240行描画をGSの表示回路で480ラインへ拡大します。9th以降のネイティブ480pパッチとは描画方式が異なります。

## 配布物

- `patch480p.py`: ISO9660を検査し、元ISOを残して別ISOを書き出すPython 3パッチャー。
- `IIDX03_SLPM-65006_480p_v1.0.xdelta`: 検証済み基準ISO専用のVCDIFF/xdelta3パッチです。[GitHub Releasesページ](https://github.com/saboten731/iidx-ps2-480p-legacy/releases)のv1.0 Release添付から入手してください。ソースリポジトリには含めていません。
- `checksums.txt`: 基準ISO、出力ISO、xdelta、Python基準出力のSHA-256。

ISO、ELF、IRX、BIOS、ゲーム素材は配布物に含めません。必ずご自身のディスクから吸い出したISOを使ってください。

適用前に元ISOのバックアップを作り、`checksums.txt` と照合できるようSHA-256を記録してください。パッチャーは元ISOを変更せず、新しい出力ファイルを作ります。

## 対応版

`SYSTEM.CNF` の `BOOT2` から実行ELFを特定し、製品番号 `SLPM_650.06` と未改変ELFのSHA-256を検証します。

```text
Supported original BOOT2 ELF SHA-256:
CD2EE5A1C50C46808927EF32A7FE8F5791AE66399DA029A75D5095CA70499321
```

PythonパッチャーはISO全体のSHA-256、総サイズ、ELFの固定セクタ位置を要求しません。ISO全体のハッシュが基準ISOと異なっていても、ISO9660から検出したBOOT2 ELFが上記SHA-256と完全一致すれば適用できます。ELFが異なる、改変済み、または既知のパッチ済みであれば出力を作らず停止します。命令の一部一致だけでは適用しません。

再構築ISOは、ELFが一致しても起動や他の変更との互換性を保証できません。入力ISO内の許可されたELF領域以外は一切変更せず、適用後にもチャンク比較で確認します。

## xdelta3で適用

[GitHub Releasesページ](https://github.com/saboten731/iidx-ps2-480p-legacy/releases)から `IIDX03_SLPM-65006_480p_v1.0.xdelta` をダウンロードしてください。xdeltaは以下の検証済み基準ISO SHA-256に一致するISO専用です。Redump一致とは確認できていないため、その表記はしていません。

```text
SLPM_650.06.Beatmania IIDX 3rd Style.iso
Size:   3,810,918,400 bytes
SHA256: D7E11CD70100675A97DDD9027D1578BDA1397959FA1562151BA9C9E7F94E16D1
```

`xdelta3` を用意し、出力先がまだ存在しないことを確認してから適用します。

```powershell
xdelta3 -d -s "SLPM_650.06.Beatmania IIDX 3rd Style.iso" `
  "IIDX03_SLPM-65006_480p_v1.0.xdelta" `
  "SLPM_650.06.Beatmania IIDX 3rd Style_480p_v1.0.iso"
```

生成ISOのSHA-256が `checksums.txt` の出力値と一致することを確認してください。元ISOのハッシュが一致しない場合はxdeltaを適用しないでください。

## Pythonで適用

Python 3.8以降を使用します。入力ISOは変更されません。デフォルト出力名は元ISO名に `_480p_v1.0.iso` を付加したものです。出力先が既にあれば上書きせず停止します。

```powershell
python patch480p.py "SLPM_650.06.Beatmania IIDX 3rd Style.iso" `
  --output "SLPM_650.06.Beatmania IIDX 3rd Style_480p_v1.0.iso"
```

パッチャーは `SYSTEM.CNF` の `BOOT2` を読み、ISO内の実際のELF extentからELFを検証・書き換えます。元ISO全体のSHA-256とサイズは適用条件ではありません。終了時に入力・出力SHA-256、出力サイズ、パッチELFのSHA-256を表示します。

## v1.0の変更

- 描画: `DISPLAY=0x001DF4FF0882B138`（240行を縦2倍、480出力ライン）。
- 映像同期設定: `SYNCV=0x00C7900001E00006`（`VDP=484`）。
- RGB/コンポーネント選択: BIOS/OSD設定を実行時に読み取る既存経路を維持します。未確認のOSD・テレビ設定での動作は保証しません。
- PMODE: GSから読み戻さず、ゲーム本来の表示環境設定が復旧します。
- SPU/IOP、音声ピッチ、譜面タイマー、判定処理は変更しません。

## 実機確認条件

ユーザーによる動作確認済みの条件:

- PS2実機、OPL、MX4SIO、D端子テレビ直結。
- GSM OFF。
- タイトル、HOW TO PLAY、選曲、実プレイ、打鍵判定、長時間動作で問題なし。

この確認結果は上記構成に限ります。別のテレビ、OSD出力設定、起動方法で同様に動くことは保証しません。

## 先行実装

[blurtic2/iidx-ps2-480p](https://github.com/blurtic2/iidx-ps2-480p) の配布構成を参考にしています。同リポジトリの主対象は9th〜16thのネイティブ480p描画であり、この3rd Styleパッチとは対象・描画経路が異なります。同リポジトリのパッチコードは本配布物に含めていません。

## ライセンス

このプロジェクトのオリジナルソースコードとドキュメントはMIT Licenseで公開しています。全文は [LICENSE](LICENSE) を参照してください。このライセンスはKonamiのゲーム、ゲーム素材、商標の権利を許諾するものではありません。本リポジトリおよびReleaseにゲームデータは含みません。

## 非公式表記

本パッチはKonamiの公式製品ではなく、Konamiから承認または支援を受けていません。ゲームを所有し、適用が法令と地域の規則に適合することを確認してください。
