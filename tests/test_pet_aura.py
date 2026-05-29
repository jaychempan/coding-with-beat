import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from coding_with_beat.pet.aura import MusicAuraWidget


def test_music_aura_starts_idle_and_transparent():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        assert aura.is_playing is False
        assert aura.burst_phase == 0.0
        assert aura.minimumWidth() >= 112
        assert aura.minimumHeight() >= 118
        assert aura.autoFillBackground() is False
    finally:
        aura.close()


def test_music_aura_set_playing_updates_state():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.set_playing(True)
        assert aura.is_playing is True

        aura.set_playing(False)
        assert aura.is_playing is False
    finally:
        aura.close()


def test_music_aura_burst_sets_visible_phase():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.burst()
        assert aura.burst_phase == 1.0
    finally:
        aura.close()


def test_music_aura_tick_advances_motion_and_fades_burst():
    app = QApplication.instance() or QApplication([])
    aura = MusicAuraWidget(sprite_size=(72, 78))
    try:
        assert app is not None
        aura.set_playing(True)
        aura.burst()
        start_rotation = aura.rotation

        aura.advance()

        assert aura.rotation != start_rotation
        assert 0.0 < aura.burst_phase < 1.0
    finally:
        aura.close()
