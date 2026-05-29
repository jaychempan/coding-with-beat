# Pet macOS Menu Bar Design

## Goal

Make the desktop pet feel like a native macOS companion instead of a Python process. On macOS, the pet should use the Coding With Beat logo as its app/menu icon, avoid showing a distracting Python Dock identity when possible, and provide a reliable way to summon the pet after it is hidden.

## User Experience

- Launching `cwb pet` still opens the desktop pet.
- The app name becomes `Coding With Beat Pet`.
- The menu bar shows a small Coding With Beat icon when the platform supports tray/menu bar icons.
- The menu bar menu includes:
  - `显示/隐藏宠物`
  - `当前播放`
  - `推荐歌曲`
  - `下一首`
  - `退出`
- Closing or hiding the pet does not quit the app while the menu bar icon exists.
- The user can summon the pet again from the menu bar icon.
- On macOS, the app attempts to hide the Dock/Cmd-Tab Python identity by switching to accessory activation policy. If AppKit is not available, the pet still runs with the logo/icon and menu actions.

## Architecture

- Add a small `macos.py` helper under `coding_with_beat/pet/`.
- Keep platform-specific code out of `window.py`.
- `pet.app.run()` owns app-level setup:
  - create/reuse `QApplication`
  - set app name
  - set window icon
  - create pet window
  - install menu bar controller
  - attempt Dock hiding on macOS
- `PetMenuBarController` owns `QSystemTrayIcon`, its `QMenu`, and show/hide command wiring.
- Existing pet window music flow remains unchanged. Menu actions call the window's existing methods.

## Error Handling

- Missing PySide6 keeps the existing install hint.
- Missing logo falls back to no custom icon.
- Missing AppKit does not fail the pet; hiding the Dock icon is best-effort.
- If `QSystemTrayIcon` is unavailable, the window remains visible and the app can still be closed through the existing context menu.

## Testing

- Unit tests cover:
  - app metadata is applied
  - icon path resolves from the repository
  - macOS Dock hiding returns `False` on non-macOS without raising
  - `run()` passes `hide_dock` into app setup
- Existing pet CLI and window tests continue to pass.
