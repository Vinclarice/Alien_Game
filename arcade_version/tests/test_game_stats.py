import json
from pathlib import Path

from game_stats import GameStats


class DummySettings:
    """Stand-in for settings.Settings -- GameStats only reads ship_limit,
    so building a real Settings() (and pulling in pygame) isn't needed."""
    ship_limit = 3


class DummyGame:
    def __init__(self):
        self.settings = DummySettings()


def test_reset_stats_sets_defaults():
    stats = GameStats(DummyGame())
    stats.ships_left = 0
    stats.score = 500
    stats.level = 4

    stats.reset_stats()

    assert stats.ships_left == 3
    assert stats.score == 0
    assert stats.level == 1


def test_high_score_defaults_to_zero_with_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stats = GameStats(DummyGame())
    assert stats.high_score == 0


def test_high_score_loads_existing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('high_score.json').write_text(json.dumps({'high_score': 4200}))

    stats = GameStats(DummyGame())

    assert stats.high_score == 4200


def test_high_score_survives_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('high_score.json').write_text('not valid json')

    stats = GameStats(DummyGame())

    assert stats.high_score == 0


def test_save_high_score_writes_current_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stats = GameStats(DummyGame())
    stats.high_score = 999

    stats.save_high_score()

    saved = json.loads(Path('high_score.json').read_text())
    assert saved == {'high_score': 999}
