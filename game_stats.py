import json
from pathlib import Path

class GameStats:
    """Track statistics for Alien Invasion."""

    def __init__(self, ai_game):
        """Initialize statistics."""
        self.settings = ai_game.settings
        self.reset_stats()

        # High score should never be reset; load any saved value from disk.
        self.high_score_file = Path('high_score.json')
        self.high_score = self._load_high_score()

    def reset_stats(self):
        """Initialize statistics that can change during the game."""
        self.ships_left = self.settings.ship_limit
        self.score = 0
        self.level = 1

    def _load_high_score(self):
        """Read the saved high score from file, if one exists."""
        if self.high_score_file.exists():
            contents = self.high_score_file.read_text()
            try:
                return json.loads(contents).get('high_score', 0)
            except json.JSONDecodeError:
                return 0
        return 0

    def save_high_score(self):
        """Write the current high score to file."""
        contents = json.dumps({'high_score': self.high_score})
        self.high_score_file.write_text(contents)
