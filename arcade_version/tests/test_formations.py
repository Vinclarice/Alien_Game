import pytest

from formations import (
    FORMATIONS,
    checkerboard,
    diamond,
    full_grid,
    hollow_box,
    pillars,
    random_formation,
    v_shape,
)

GRID_SIZES = [(1, 1), (3, 3), (8, 5), (12, 1), (1, 12)]


@pytest.mark.parametrize("cols,rows", GRID_SIZES)
@pytest.mark.parametrize("formation", FORMATIONS)
def test_formation_cells_are_in_bounds(formation, cols, rows):
    """Every formation should only ever place aliens inside the grid it
    was given -- a cell outside (cols, rows) would put an alien off the
    edge of the fitted grid in _create_fleet()."""
    cells = formation(cols, rows)
    for c, r in cells:
        assert 0 <= c < cols
        assert 0 <= r < rows


def test_full_grid_fills_every_cell():
    cells = full_grid(4, 3)
    assert cells == {(c, r) for r in range(3) for c in range(4)}


def test_v_shape_is_no_narrower_at_the_bottom_than_the_top():
    cells = v_shape(9, 5)

    def width(row):
        cols_in_row = [c for c, r in cells if r == row]
        return max(cols_in_row) - min(cols_in_row) if cols_in_row else 0

    assert width(0) <= width(4)


def test_diamond_is_symmetric_around_its_center_row():
    cols, rows = 9, 7
    cells = diamond(cols, rows)
    center_row = rows // 2
    for r in range(rows):
        mirrored = center_row - (r - center_row)
        if 0 <= mirrored < rows:
            width_r = {c for c, row in cells if row == r}
            width_m = {c for c, row in cells if row == mirrored}
            assert len(width_r) == len(width_m)


def test_pillars_only_uses_every_third_column():
    cells = pillars(6, 3)
    assert {c for c, r in cells} == {0, 3}


def test_checkerboard_only_keeps_matching_parity_cells():
    cells = checkerboard(4, 4)
    for c, r in cells:
        assert (c + r) % 2 == 0


def test_hollow_box_has_no_interior_cells():
    cols, rows = 5, 5
    cells = hollow_box(cols, rows)
    interior = {(c, r) for r in range(1, rows - 1) for c in range(1, cols - 1)}
    assert not (cells & interior)


@pytest.mark.parametrize("cols,rows", [(6, 4), (10, 6), (3, 2)])
def test_random_formation_returns_nonempty_valid_cells(cols, rows):
    for _ in range(25):
        cells, name = random_formation(cols, rows)
        assert cells, f"random_formation returned no cells ({name})"
        assert name in {f.__name__ for f in FORMATIONS}
        for c, r in cells:
            assert 0 <= c < cols
            assert 0 <= r < rows
