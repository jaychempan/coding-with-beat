import plistlib

from scripts.build_macos_app import build_app


def test_build_app_creates_codebeat_bundle(tmp_path):
    app_path = build_app(tmp_path)

    assert app_path.name == "CodeBeat.app"
    assert (app_path / "Contents" / "Info.plist").exists()
    assert (app_path / "Contents" / "MacOS" / "CodeBeat").exists()
    assert (app_path / "Contents" / "Resources" / "waveform_app_icon.svg").exists()
    assert (app_path / "Contents" / "Resources" / "waveform_menu_bar.svg").exists()
    assert (app_path / "Contents" / "Resources" / "CodeBeat.icns").exists()


def test_build_app_writes_expected_info_plist(tmp_path):
    app_path = build_app(tmp_path)
    plist_path = app_path / "Contents" / "Info.plist"

    with plist_path.open("rb") as f:
        plist = plistlib.load(f)

    assert plist["CFBundleName"] == "CodeBeat"
    assert plist["CFBundleDisplayName"] == "CodeBeat"
    assert plist["CFBundleIdentifier"] == "top.codebeat.CodeBeat"
    assert plist["CFBundleExecutable"] == "CodeBeat"
    assert plist["CFBundleIconFile"] == "CodeBeat.icns"
    assert plist["LSUIElement"] is False


def test_build_app_launcher_runs_codebeat_app_command(tmp_path):
    app_path = build_app(tmp_path)
    launcher = app_path / "Contents" / "MacOS" / "CodeBeat"

    text = launcher.read_text(encoding="utf-8")

    assert "python -m coding_with_beat app" in text
    assert 'export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"' in text
    assert "BUILT_PY=" in text
    assert "~/.coding-with-beat/repo-path" not in text
    assert "$HOME/.coding-with-beat/repo-path" in text
    assert launcher.stat().st_mode & 0o111
