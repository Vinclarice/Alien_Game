"""Typed configuration objects for weapons and alien variants.

These used to be plain dicts in settings.py, keyed by string (e.g.
weapon['bullet_count']). That made typos in a key silently return a
KeyError deep inside game logic instead of failing fast, and gave no
autocomplete/type-checking help. Dataclasses fix both: attribute access
is checked by tooling, and every field has a documented type/default.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class WeaponType:
    """One weapon preset the ship can fire (switch with 1/2/3)."""

    speed: float
    width: int
    height: int
    color: Color
    bullet_count: int  # how many bullets one shot fires
    spread_angle: float = 0  # degrees between adjacent bullets in a fan
    piercing: bool = False  # survives hitting an alien instead of dying
    pierce_count: int = 1  # aliens a piercing bullet can hit before dying
    max_active: Optional[int] = None  # cap on bullets of this type in the air


@dataclass(frozen=True)
class AlienType:
    """One alien variant, recolored/rescaled from the same base image."""

    scale: float
    tint: Optional[Color]
    hits_required: int  # bullet hits needed to destroy it
    points_multiplier: float  # scales settings.alien_points
    speed_multiplier: float  # scales settings.alien_speed for this type
    weight: float  # relative odds of this type when the fleet is built
