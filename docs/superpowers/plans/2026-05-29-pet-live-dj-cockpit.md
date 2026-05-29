# Pet Live DJ Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live motion, now-playing/lyrics, and common CWB command controls to the CodeBeat DJ panel.

**Architecture:** Extend `PetMusicClient` with snapshot/control methods and keep the PySide UI orchestration inside `CodeBeatDjPanel`. Use `QTimer` for low-frequency motion and visible-only snapshot polling.

**Tech Stack:** Python, PySide6, pytest, ruff.

---

## Tasks

- [ ] Add `PetMusicClient.now_playing_snapshot()` and `control()`.
- [ ] Add focused tests for live snapshot rendering, command parsing, and motion timer.
- [ ] Implement live labels, command chips, prompt command parsing, and motion paint state.
- [ ] Run focused and full test suites.
- [ ] Rebuild/restart `CodeBeat.app`.
- [ ] Commit on branch `pet`.
