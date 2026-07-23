from enum import Enum, auto


class GameState(Enum):
    """The screen/mode Alien Invasion is currently in.

    Replaces the old game_active boolean, which couldn't distinguish
    "hasn't started yet" from "just lost" -- both looked identical
    (play button, cleared board), so there was no way to show a
    game-over message or final score.
    """

    MENU = auto()
    PLAYING = auto()
    GAME_OVER = auto()
