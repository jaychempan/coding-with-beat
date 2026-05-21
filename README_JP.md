# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-21_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![Website](https://img.shields.io/badge/website-codebeat.top-9bbc0f?style=flat-square)](https://codebeat.top)

> **バイブコーディング中に歌って踊ったのはいつだっけ？**
>
> そう、覚えていないよね。

![](assets/welcome_log.png)

Claude Code に住むピクセルアート DJ コンパニオン。音楽を流し、歌詞を表示し、コミット成功を祝い、テスト失敗には一緒にパニックになります。

[English README](README.md) ／ [中文文档](README_CN.md)

---

## 機能紹介

- **MCP サーバー** — 21 個のツールを Claude Code に公開。「lofi かけて」「次の曲に」「今何が流れてる？」と自然に話しかけるだけで動きます。
- **音楽ソース** — Apple Music（AppleScript、GUI 不要）、ローカルファイル（afplay）、QQ Music（検索＋プレビュー）。
- **ピクセル UI** — アルバムアートを半ブロック ANSI 文字でレンダリング。GameBoy レトロボーダー＆疑似スペクトラムイコライザー付き。
- **DJ Buddy** — ヘッドフォンをつけたピクセルキャラクター。コーディング状態に合わせて表情が変わります。テスト失敗？一緒にパニックに。
- **バイブエンジン** — CC フック（PreToolUse / PostToolUse / SessionStart / Stop）でリアルタイムに状況を把握し、雰囲気を自動調整。`git commit` したら勝利ポーズ。テストが爆発したらパニックモードへ。
- **ステータスライン** — 1 行に収まる表示：顔 ＋ 現在のトラック ＋ 進捗バー。
- **フォーカスモード** — 25/5 ポモドーロタイマー内蔵、ステータスラインに表示。

---

## インストール

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

手動インストール：

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

新しいシェルと新しい Claude Code セッションを開き、ステータスラインに `(•_•)` が表示されたらインストール完了です。

---

## 使い方

### Claude に話しかけるだけ

```
lofi をかけて
この曲スキップして
今何が流れてる？
一時停止して
```

### `/cwb` コマンド

```
/cwb play 米津玄師          # 検索して再生
/cwb play lofi beats
/cwb next                   # 次の曲
/cwb pause                  # 一時停止
/cwb np                     # 再生中の曲
/cwb like                   # お気に入りに追加
/cwb volume 70              # 音量設定
/cwb watch                  # ライブプレイヤー（q で終了）
/cwb karaoke                # フルスクリーンカラオケ（q で終了）
/cwb lyrics                 # 歌詞ウィンドウ
/cwb bar auto               # ステータスライン：auto / show / hide
```

### `watch` / `karaoke` キーボードショートカット

| キー | 操作 |
|------|------|
| `Space` | 再生 / 一時停止 |
| `n` | 次の曲 |
| `p` | 前の曲 |
| `l` | お気に入り |
| `q` | 終了 |

---

## ステータスライン

インストール後、Claude Code の下部にステータスラインが表示されます：

```
(•_•) ⚡  ▶ 雨爱 — 杨丞琳  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ 不忍揭曉的劇情
```

| 要素 | 例 | 説明 |
|------|----|------|
| DJ の顔 | `(•_•)` `(^_^)` `(T_T)` | Buddy の気分。コーディングイベントで変化 |
| アクティビティ | `⚡` / `·` / _(なし)_ | `⚡` = 15 秒以内にツール呼び出し；`·` = 90 秒以内 |
| 再生アイコン | `▶` / `▷` / `❚❚` | 再生中は点滅；一時停止中は ❚❚ |
| トラック | `曲名 — アーティスト  ██████░░░` | タイトル ＋ アーティスト ＋ 進捗バー |
| バイブ | `[build]` `[focus]` 等 | 現在のコーディング雰囲気 |
| ポモドーロ | `🍅 work 24:15` | フォーカスモード中のみ表示 |
| ビートウェーブ | `▁▂▃▄▅` | ビートに合わせて上下；一時停止中は暗く |
| 歌詞 | `│ ♪ 歌詞テキスト` | 現在の LRC 歌詞 |

---

## CLI

```
cwb play [query]        # 検索して再生、または再開
cwb pause               # 一時停止
cwb next                # 次の曲
cwb prev                # 前の曲
cwb np                  # 再生中の曲
cwb like                # お気に入りに追加
cwb volume <0-100>      # 音量設定
cwb seek <t>            # シーク：秒数（90）または mm:ss（1:30）
cwb mode <mode>         # shuffle | sequential | repeat | repeat_one
cwb player              # フルピクセルプレイヤー
cwb watch               # ライブ TUI（q で終了）
cwb karaoke             # フルスクリーンカラオケ（q で終了）
cwb lyrics              # 歌詞ウィンドウ
cwb history [n]         # 最近再生した n 曲
cwb bar <show|hide|auto> # ステータスライン表示設定
cwb status              # 現在の状態
```

---

## 音楽ソース

| 機能 | Apple Music | ローカルファイル | QQ Music |
|------|-------------|-----------------|----------|
| 再生情報 | ✓ | ✓ | ⚠ プレビュー時のみ |
| 再生 / 一時停止 | ✓ | ✓ | ✓ |
| 次 / 前の曲 | ✓ | ✓ | ✓ |
| シーク | ✓ | ⚠ 再起動ベース | ⚠ プレビュー時のみ |
| 音量 | ✓ | ✓ | ⚠ 粗いステップ制御 |
| お気に入り | ✓ | ✗ | ✓ |
| カバーアート | ✓ | ✓ | ✓ |
| フル再生 | ✓ サブスク必要 | ✓ | ✗ 30 秒プレビューのみ |
| 再生モード | ✓ | ✗ | ✓ |

> QQ Music に公式 API はありません。メタデータは公開エンドポイントから取得し、音声は afplay で 30 秒プレビューとして再生されます。フル再生には QQ Music デスクトップアプリが必要です。

---

## アンインストール

```bash
./uninstall.sh           # 設定・コマンド・PATH を削除
./uninstall.sh --purge   # 同上 ＋ ~/.coding-with-beat/ を削除
```

---

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) をご覧ください。
