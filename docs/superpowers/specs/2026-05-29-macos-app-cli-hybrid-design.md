# macOS App + CLI Hybrid Design

## Goal

Build a local macOS app entry point for Coding With Beat while preserving the existing terminal-first `cwb` workflow. The app should be double-clickable as `CodeBeat.app`, live in the menu bar, use a visually restrained waveform logo, and provide controls for the pet and background service. The CLI should remain available for all terminal and AI-agent workflows.

## Recommended Shape

Use a hybrid installer-managed app:

- `CodeBeat.app` is a lightweight local app wrapper, generated from the current checkout.
- `cwb` remains installed through the existing venv and symlink flow:
  - venv: `~/.coding-with-beat/venv`
  - CLI link: `~/.local/bin/cwb`
  - repo path: `~/.coding-with-beat/repo-path`
- The app launches Python from the installed venv when available, or falls back to the current interpreter during development.
- The app starts a menu-bar controller, not a full marketing GUI.

## User Experience

Double-clicking `CodeBeat.app` should:

- start the app without requiring Terminal to stay open
- show a waveform menu-bar icon that is visually smaller than the current full-size logo and does not look larger than nearby menu-bar icons
- hide the Dock/Python identity by default
- show or summon the desktop pet
- keep `cwb` commands usable in Terminal

The menu bar should expose:

- `显示/隐藏宠物`
- `当前播放`
- `推荐歌曲`
- `下一首`
- `重启 DJ 服务`
- `安装/修复终端命令`
- `打开终端使用说明`
- `退出`

## Build And Install Flow

Add a local app builder:

- `scripts/build_macos_app.py`
- output: `dist/CodeBeat.app`
- app icon: waveform logo with enough transparent padding that it does not appear oversized in Finder, Launchpad, or the Dock
- menu-bar icon: a dedicated transparent waveform mark with a smaller visual footprint than the app icon
- app bundle metadata:
  - `CFBundleName`: `CodeBeat`
  - `CFBundleDisplayName`: `CodeBeat`
  - `CFBundleIdentifier`: `top.codebeat.CodeBeat`
  - `LSUIElement`: `true`

The app bundle can use a shell launcher at first:

- read `~/.coding-with-beat/repo-path`
- prefer `~/.coding-with-beat/venv/bin/python`
- run `python -m coding_with_beat app`
- log to `~/.coding-with-beat/logs/app.log` and `app.err.log`

This is a local development app, not a signed distributable `.dmg` yet.

## Python Entrypoint

Add a new command:

```bash
cwb app
python -m coding_with_beat app
```

It should:

- start the same menu-bar app shell used by `cwb pet`
- ensure the desktop pet can be shown/hidden
- provide service repair actions
- keep running until the user chooses `退出`

`cwb pet` remains a direct pet launcher. `cwb app` is the Mac control center.

## Service And CLI Repair

The app should reuse existing mechanisms where possible:

- `cwb restart` for MCP server restart
- existing installer-created `~/.local/bin/cwb`
- existing `~/.coding-with-beat/repo-path`

The first implementation can provide repair actions by running:

```bash
<repo>/install.sh
```

This is simple and consistent with the current installer. Later versions can split out smaller repair commands.

## Scope Boundaries

In scope for the first version:

- generate local `.app`
- add `cwb app`
- menu-bar app shell
- pet summon/hide
- restart service action
- open a usage/help panel or Terminal help text
- install/repair CLI action

Out of scope for the first version:

- PyInstaller runtime bundling
- `.dmg` generation
- code signing
- notarization
- auto-update
- replacing the terminal CLI

## Testing

Automated tests should cover:

- app command registration
- builder creates the expected `.app` structure
- generated `Info.plist` contains `LSUIElement=true`
- generated launcher points at `python -m coding_with_beat app`
- app menu exposes the expected actions
- repair commands are built without executing the real installer in tests

Manual local verification:

- run `python scripts/build_macos_app.py`
- open `dist/CodeBeat.app`
- confirm menu-bar waveform icon appears
- confirm the app icon and menu-bar icon do not look larger than neighboring macOS icons
- confirm pet can be shown/hidden
- confirm `cwb` still works in Terminal
- confirm no traceback in app logs

## Risks

- Unsigned local apps may trigger Gatekeeper warnings if moved between machines. This is acceptable for the local development version.
- macOS Dock hiding is best-effort unless the app bundle has `LSUIElement=true`; the bundle path is the reliable path.
- Running the full installer from a menu action can take time. The first version should show a status bubble or log message rather than blocking silently.
