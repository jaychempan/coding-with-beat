import json
import plistlib

from scripts.build_macos_app import _existing_pet_files, build_app


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
    assert 'LOG_DIR="$HOME/Library/Logs/CodeBeat"' in text
    assert "$HOME/.coding-with-beat/logs" not in text
    assert launcher.stat().st_mode & 0o111


def test_build_app_writes_resource_manifest(tmp_path):
    app_path = build_app(tmp_path)
    manifest_path = app_path / "Contents" / "Resources" / "manifest.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["version"] == 1
    assert manifest["appVersion"] == "0.1.0"
    assert "assets/waveform_app_icon.svg" in manifest["resources"]["assets"]
    assert "assets/waveform_menu_bar.svg" in manifest["resources"]["assets"]
    assert "pets/codebeat-buddy/pet.json" in manifest["resources"]["pets"]
    assert "pets/codebeat-buddy/spritesheet.png" in manifest["resources"]["pets"]


def test_existing_pet_files_excludes_hidden_system_files(tmp_path):
    pet_root = tmp_path / "pets"
    buddy = pet_root / "codebeat-buddy"
    hidden_dir = buddy / ".generated"
    buddy.mkdir(parents=True)
    hidden_dir.mkdir()

    (pet_root / ".DS_Store").write_text("metadata", encoding="utf-8")
    (buddy / "pet.json").write_text("{}", encoding="utf-8")
    (buddy / ".DS_Store").write_text("metadata", encoding="utf-8")
    (hidden_dir / "sprite.png").write_text("hidden", encoding="utf-8")

    assert _existing_pet_files(pet_root) == ["pets/codebeat-buddy/pet.json"]
