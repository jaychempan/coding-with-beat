# CodeBeat macOS Unified App Design

## Goal

Turn Coding With Beat into a single macOS application that users install and run as `CodeBeat.app`. The app should include the official pet Byte, own the menu-bar and Dock identity, manage the local MCP service, and provide one-click integration management for Claude Code and Codex.

The first unified release is macOS-only. Cross-platform packaging, cloud accounts, auto-update, and a full marketplace are out of scope.

## Product Shape

`CodeBeat.app` becomes the primary product. The terminal `cwb` command remains available for advanced users and agent hooks, but normal setup should happen inside the app.

The app provides:

- a stable macOS Dock and menu-bar identity
- a menu-bar control center
- a Byte pet entry point
- a settings window for music sources and integrations
- lifecycle management for the local MCP service
- install, repair, and remove actions for Claude Code and Codex integrations

## Recommended Technical Approach

Use a bundled Python macOS app for the first production-ready version:

- package the existing Python code, PySide6 UI, assets, commands, skills, and MCP server into the app bundle
- include a private Python runtime and site-packages inside `CodeBeat.app`
- stop relying on a user-created `~/.coding-with-beat/venv` for the normal app path
- keep development commands working from the repository during local development

This is a step beyond the current shell-wrapper app. The current wrapper eventually runs `exec python -m coding_with_beat app`, which can expose a Python Dock identity. The unified app should run from a real app bundle with a stable executable, icon, bundle identifier, and resource layout.

## App Bundle Layout

Recommended bundle shape:

```text
CodeBeat.app/
  Contents/
    Info.plist
    MacOS/
      CodeBeat
    Resources/
      CodeBeat.icns
      assets/
      python/
      app/
      integrations/
```

`Contents/MacOS/CodeBeat` should be the stable app executable or launcher. It should not leave the visible app identity as a generic Python process.

`Contents/Resources/python/` contains the embedded runtime and dependencies.

`Contents/Resources/app/` contains the installed `coding_with_beat` package and bundled data files.

`Contents/Resources/integrations/` contains versioned templates for Claude Code and Codex commands, skills, hooks, and MCP configuration.

## Runtime Components

### App Shell

The app shell owns macOS-facing behavior:

- app metadata and icon
- menu-bar item
- Dock visibility
- settings window
- launch-at-login preference
- service status and restart commands

The first implementation can continue using PySide6 for UI. If the product grows, a later SwiftUI shell can replace the PySide6 shell while keeping the Python backend.

### Backend Service

The app owns the MCP service lifecycle:

- start the local HTTP MCP server when the app launches
- expose service status in the settings window
- restart the server after crashes
- write logs under `~/Library/Logs/CodeBeat/`
- store user settings under `~/Library/Application Support/CodeBeat/`

The existing `~/.coding-with-beat/` paths can remain as a migration source, but new app-managed state should use standard macOS application paths.

### CLI Compatibility

The app should optionally install a `cwb` shim into `~/.local/bin` or another user-selected location. The shim should call into the bundled app helper, not a repo checkout venv.

The CLI remains useful for:

- terminal users
- Claude/Codex hooks
- debugging
- scripted playback commands

It should not be required for normal installation.

## User Experience

### First Launch

On first launch, `CodeBeat.app` opens a compact setup window:

- confirm Apple Music / QQ Music / local files availability
- show MCP service status
- offer Claude Code integration
- offer Codex integration
- show Byte as the default pet

The setup should avoid terminal instructions unless an action fails.

### Menu Bar

The menu-bar menu should include:

- `显示/隐藏 Byte`
- `当前播放`
- `推荐歌曲`
- `下一首`
- `打开 CodeBeat`
- `Claude Code 集成`
- `Codex 集成`
- `重启 DJ 服务`
- `退出`

### Byte Pet

Byte is the default official pet. The internal slug can remain `codebeat-buddy` for compatibility, but all user-facing labels should say `Byte`.

The Byte page should support:

- show/hide
- switch Petdex pet
- reset to Byte
- choose whether the Dock icon is visible
- choose whether the menu-bar icon is visible

## Claude Code Integration

The app should manage Claude Code integration through idempotent install, repair, and remove actions.

Managed items:

- commands under `~/.claude/commands/`
- skills under `~/.claude/skills/`
- MCP server configuration
- statusline and hook configuration
- project-level instructions only when the user explicitly opts in

The app should detect:

- Claude Code config directory exists
- expected command links/files exist
- expected skills exist
- MCP URL points at the app-managed local service
- hooks are installed and owned by CodeBeat

The repair action should only touch CodeBeat-owned blocks and files.

## Codex Integration

The app should manage Codex integration through the same model:

- install or update `~/.codex/config.toml`
- install or update `~/.codex/hooks.json`
- install CodeBeat skills under `~/.codex/skills/`
- configure tool approvals for the CodeBeat MCP tools
- remove only CodeBeat-owned blocks and files

The current `scripts/install_codex_config.py` already has the right ownership pattern with `_owner = "coding-with-beat"` and marked config blocks. The app should reuse that logic behind a UI action instead of asking the user to run a script.

## Packaging Strategy

First production packaging target:

- macOS `.app` bundle
- generated `.dmg`
- unsigned local builds for development
- signed and notarized builds before public distribution

Packaging candidates:

- PyInstaller: pragmatic first choice for bundling Python, PySide6, assets, and helper files
- py2app: possible, but less predictable with modern PySide6
- SwiftUI shell plus embedded Python: best long-term app identity, but higher first-version cost

Recommendation: ship the first unified app with PyInstaller or an equivalent bundled-Python approach. Revisit SwiftUI once the product flow is stable.

## Migration

On first launch, the app should read existing state from:

- `~/.coding-with-beat/pet.json`
- `~/.coding-with-beat/mcp-url`
- `~/.coding-with-beat/repo-path`
- existing Claude Code and Codex config files

It should then write app-owned settings to:

- `~/Library/Application Support/CodeBeat/settings.json`
- `~/Library/Logs/CodeBeat/`

Do not delete old state during migration. Leave rollback possible.

## Error Handling

If the MCP service fails to start:

- show the failure in the app status page
- keep the UI open
- offer restart and open-log actions

If Claude or Codex config files are malformed:

- back up the file before writing
- show a clear repair failure
- do not overwrite unrelated user config

If Apple Music or QQ Music is unavailable:

- keep the app running
- show the source as unavailable
- allow local file mode and integration management to continue

## Testing

Automated tests should cover:

- app bundle layout generation
- `Info.plist` bundle id, display name, and icon
- bundled resource manifest includes assets, commands, skills, and pet files
- Claude integration install, repair, and remove logic against temporary config directories
- Codex integration install, repair, and remove logic against temporary config directories
- service lifecycle manager start, stop, restart, and crash recovery behavior
- migration from `~/.coding-with-beat` state into app support state
- Byte remains the user-facing name for the bundled default pet

Manual verification should cover:

- drag `CodeBeat.app` into Applications and launch it
- Dock icon remains CodeBeat, not Python
- menu-bar icon appears and has the expected size
- Byte can be shown and hidden
- MCP service starts without a terminal
- Claude Code can call CodeBeat tools after app-managed install
- Codex can call CodeBeat tools after app-managed install
- app logs are readable from the settings window

## Phasing

### Phase 1: Unified App Foundation

- introduce app-owned directories under `~/Library/Application Support/CodeBeat`
- create a stable app resource manifest
- add a service lifecycle manager
- move current menu-bar shell toward app-owned service control

### Phase 2: Integration Manager

- extract Claude Code install logic into reusable Python functions
- extract Codex install logic into reusable Python functions
- build app UI for install, repair, remove, and status
- keep shell installers as compatibility wrappers around the same functions

### Phase 3: Bundled macOS App

- build a bundled `.app` with embedded Python and dependencies
- include commands, skills, assets, and pet files
- generate `.dmg`
- verify Dock identity and menu-bar behavior

### Phase 4: Distribution Hardening

- sign and notarize release builds
- add crash logs and diagnostics export
- add optional launch-at-login
- add update checking after the first stable distribution path exists

## Current State To Preserve

The repository already has a lightweight `CodeBeat.app` builder in
`scripts/build_macos_app.py`. It creates the app bundle, writes
`Info.plist`, generates `CodeBeat.icns`, and installs a shell launcher that
executes `python -m coding_with_beat app` from the checkout.

The current `coding_with_beat.app` entrypoint delegates directly to the
desktop pet app. It respects saved pet chrome settings and starts Byte through
the existing Petdex path. This behavior should remain available during the
transition.

The unified app should evolve this wrapper instead of deleting it in one step:

- keep `scripts/build_macos_app.py` as the local development builder
- add a production bundle path that embeds Python and app resources
- keep `python -m coding_with_beat app` working from a checkout
- keep existing pet tests and app-builder tests passing
- add new tests around the bundled resource manifest and service lifecycle

## Architecture Boundaries

The unified app should split responsibilities into small modules so the app
shell, service manager, integrations, and packaging can be tested separately.

Recommended modules:

- `coding_with_beat/app.py`: top-level app entrypoint and dependency wiring
- `coding_with_beat/app_paths.py`: standard macOS paths and legacy path lookup
- `coding_with_beat/app_settings.py`: app-level settings load, save, migration
- `coding_with_beat/service_manager.py`: MCP server lifecycle control
- `coding_with_beat/integrations/claude.py`: Claude Code status, install, repair, remove
- `coding_with_beat/integrations/codex.py`: Codex status, install, repair, remove
- `coding_with_beat/integrations/resources.py`: bundled template discovery and version checks
- `coding_with_beat/app_ui/`: settings window and integration status views

Existing pet modules should remain focused on Byte and desktop-pet interaction.
The pet should call app services through a narrow API instead of owning service
startup, installer logic, or app-wide settings.

## App Paths

New app-managed files should use macOS application locations:

```text
~/Library/Application Support/CodeBeat/
  settings.json
  service.json
  integrations.json
  pet/
  queues/

~/Library/Logs/CodeBeat/
  app.log
  app.err.log
  mcp.log
  mcp.err.log
```

Legacy files under `~/.coding-with-beat/` remain readable:

- `pet.json`
- `mcp-url`
- `repo-path`
- `search_queue.json`
- `state.json`
- existing logs

The migration should copy or translate settings into the new app support
directory, but it should not delete legacy files. CLI commands may continue to
read legacy files until the CLI is deliberately migrated.

## Settings Model

The app settings file should be a small JSON document with explicit versioning:

```json
{
  "version": 1,
  "source": "apple_music",
  "pet": {
    "slug": "codebeat-buddy",
    "showDockIcon": true,
    "showMenuBarIcon": true
  },
  "service": {
    "mcpUrl": "http://127.0.0.1:8765/mcp",
    "startOnLaunch": true,
    "restartOnCrash": true
  },
  "integrations": {
    "claude": {
      "enabled": false
    },
    "codex": {
      "enabled": false
    }
  }
}
```

The schema should be permissive when reading older versions. Unknown keys are
preserved where practical so future app versions do not destroy user settings.

## Service Lifecycle Contract

The app-managed MCP service should expose a simple state model:

- `stopped`: no child process or managed LaunchAgent is running
- `starting`: app has requested startup and is waiting for the health check
- `running`: health check succeeded against the configured MCP URL
- `degraded`: process exists but health check or tool call failed
- `crashed`: managed process exited unexpectedly

The service manager should provide:

- `status()`
- `start()`
- `stop()`
- `restart()`
- `health_check()`
- `open_logs()`

For the first bundled release, prefer a child process owned by the app unless
LaunchAgent behavior is needed for agent access when the UI is closed. A child
process is easier to test and keeps ownership clear. If background availability
after app quit becomes required, introduce an app-owned LaunchAgent in a later
phase with the same service-manager API.

The service should be started from the bundled Python runtime in production and
from the checkout Python in development. The UI should show which mode is
active so support logs are understandable.

## Integration Status Model

Claude Code and Codex should share the same integration status vocabulary:

- `not_found`: the target app config directory does not exist
- `not_installed`: config directory exists but no CodeBeat-owned files or blocks exist
- `installed`: expected files, blocks, and MCP URL match the bundled version
- `outdated`: CodeBeat-owned files or blocks exist but version markers are older
- `broken`: expected CodeBeat-owned items are missing or malformed
- `unknown`: config exists but cannot be parsed safely

Each integration manager should return both a machine-readable status and
human-readable details for the settings window. The install and repair buttons
should be disabled while an operation is running and should always write a
timestamped backup before mutating user config.

## Integration Ownership

All installed files and config blocks need durable ownership markers:

- owner: `coding-with-beat`
- product: `CodeBeat`
- integration: `claude` or `codex`
- resource version: app bundle version or resource manifest version

The remove action must delete only files and blocks with these markers. If a
config file contains unmarked user content, the integration manager must leave
it intact.

For symlinks, the manager should treat the symlink as owned only when its path
is inside a CodeBeat-owned integration directory or the linked file contains a
CodeBeat ownership marker.

## Bundled Resource Manifest

The production bundle should include a manifest that lists every resource the
app needs at runtime:

```json
{
  "version": 1,
  "appVersion": "0.1.0",
  "resources": {
    "assets": [],
    "pets": [],
    "claude": [],
    "codex": [],
    "commands": [],
    "skills": []
  }
}
```

The builder should generate this manifest during packaging. Tests should assert
that Byte files, app icons, Codex installer templates, Claude/Codex skills, and
commands are present. Runtime code should use the manifest instead of assuming
repository-relative paths when running from `CodeBeat.app`.

## UI Structure

The first unified settings window should be compact and operational:

- status header with service state and current MCP URL
- music source selector for Apple Music, QQ Music, and local files
- Byte section with show/hide, reset to Byte, Dock icon, and menu-bar icon
- Claude Code integration row with status, install, repair, remove, and open config
- Codex integration row with status, install, repair, remove, and open config
- diagnostics row with restart service, open logs, and export diagnostics

The app should avoid explanatory onboarding screens after setup. The steady
state is a small control center that shows status and gives direct actions.

## Diagnostics Export

The app should provide an export action that writes a zip file containing:

- app settings with tokens and local-only secrets redacted
- service status snapshot
- integration status snapshot
- recent app and MCP logs
- bundle version and resource manifest version
- Python runtime version
- macOS version

The export should not include music library contents, search queues, full
listening history, or arbitrary Claude/Codex user config.

## Security And Privacy

The local MCP service should bind to `127.0.0.1` by default. The app should not
open a public network listener during the first unified release.

Config writes should be local and explicit. The app should not install Claude
Code or Codex project-level instructions unless the user chooses that action for
a specific project path.

Diagnostics should redact absolute home directory paths where possible in UI
summaries, while keeping full paths in local logs when they are needed for
debugging.

## Compatibility Rules

The app and CLI should both understand the MCP URL file during the transition:

- app writes the canonical MCP URL to app support state
- app mirrors the URL to `~/.coding-with-beat/mcp-url` for existing hooks
- CLI reads app support state first once migrated, then falls back to legacy state
- installers should keep writing compatibility files until all hooks use app paths

The terminal `cwb` command should remain stable. Existing commands such as
`cwb server`, `cwb restart`, `cwb pet`, `cwb app`, `cwb play`, and `cwb np`
should continue to work from a development checkout.

## Release Acceptance Criteria

The first unified macOS release is ready when:

- a fresh user can launch `CodeBeat.app` without creating a Python virtualenv
- Dock and menu-bar identities consistently show CodeBeat branding
- Byte appears by default and can be hidden, shown, and reset
- the app starts and restarts the local MCP service without terminal commands
- Claude Code integration can be installed, detected, repaired, and removed
- Codex integration can be installed, detected, repaired, and removed
- config mutations are backed up and limited to CodeBeat-owned files or blocks
- existing CLI workflows still work from a checkout
- automated tests cover the resource manifest, settings migration, service manager, and integration managers
- manual verification passes from a dragged `CodeBeat.app` in `/Applications`

## Open Decisions

- Whether the first production bundle uses PyInstaller or a custom launcher.
- Whether quitting the app should stop the MCP service or keep it alive through an app-owned LaunchAgent.
- Whether `cwb` shim installation is automatic or opt-in.
- Whether public releases require notarization before the first external beta.
