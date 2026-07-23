import pytest

from settings import Settings


def test_increase_speed_scales_ship_alien_and_bullet_speed():
    settings = Settings()
    base_ship_speed = settings.ship_speed
    base_alien_speed = settings.alien_speed
    base_bullet_multiplier = settings.bullet_speed_multiplier

    settings.increase_speed()

    assert settings.ship_speed == pytest.approx(
        base_ship_speed * settings.speedup_scale)
    assert settings.alien_speed == pytest.approx(
        base_alien_speed * settings.speedup_scale)
    assert settings.bullet_speed_multiplier == pytest.approx(
        base_bullet_multiplier * settings.speedup_scale)


def test_increase_speed_scales_alien_points():
    settings = Settings()
    base_points = settings.alien_points

    settings.increase_speed()

    assert settings.alien_points == int(base_points * settings.score_scale)


def test_initialize_dynamic_settings_resets_to_base_values():
    settings = Settings()
    settings.increase_speed()
    settings.increase_speed()

    settings.initialize_dynamic_settings()

    assert settings.ship_speed == 7.5
    assert settings.alien_speed == 1.0
    assert settings.bullet_speed_multiplier == 1.0
    assert settings.alien_points == 50
    assert settings.fleet_direction == 1


def test_alien_type_weights_sum_to_one():
    """random.choices() doesn't require weights to sum to 1, but if they
    drift from 1.0 the weight comment in settings.py ("odds of each
    type") stops being an accurate description -- worth catching."""
    settings = Settings()
    total = sum(t.weight for t in settings.alien_types.values())
    assert total == pytest.approx(1.0)


def test_weapon_types_have_sane_values():
    settings = Settings()
    for weapon in settings.weapon_types.values():
        assert weapon.bullet_count >= 1
        assert weapon.speed > 0
        assert weapon.width > 0
        assert weapon.height > 0
