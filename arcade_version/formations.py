import random

"""Fleet formation layouts.

Each formation function takes the maximum grid size that fits on screen
(cols x rows) and returns the set of (col, row) grid cells that should
hold an alien. AlienInvasion._create_fleet() picks one at random and
places an alien at each returned cell (via the existing grid spacing
math in _create_alien), so formations plug in without touching how
aliens are actually positioned or animated.
"""

def full_grid(cols, rows):
    """Every cell filled -- the classic uniform grid."""
    return {(c, r) for r in range(rows) for c in range(cols)}

def v_shape(cols, rows):
    """A V that widens going down, with its point at the top center."""
    center = cols // 2
    cells = set()
    for r in range(rows):
        left, right = center - r, center + r
        if 0 <= left < cols:
            cells.add((left, r))
        if 0 <= right < cols:
            cells.add((right, r))
    return cells

def diamond(cols, rows):
    """A diamond, widest across its middle row."""
    center_row, center_col = rows // 2, cols // 2
    max_half = max(min(center_row, center_col), 1)
    cells = set()
    for r in range(rows):
        half_width = max_half - abs(r - center_row)
        if half_width < 0:
            continue
        for c in range(center_col - half_width, center_col + half_width + 1):
            if 0 <= c < cols:
                cells.add((c, r))
    return cells

def pillars(cols, rows):
    """Vertical columns of aliens with gaps between them."""
    return {(c, r) for c in range(cols) for r in range(rows) if c % 3 == 0}

def checkerboard(cols, rows):
    """Alternating cells for a looser, less rigid grid."""
    return {(c, r) for r in range(rows) for c in range(cols)
        if (c + r) % 2 == 0}

def hollow_box(cols, rows):
    """Just the outer border of the grid, empty in the middle."""
    return {(c, r) for r in range(rows) for c in range(cols)
        if r in (0, rows - 1) or c in (0, cols - 1)}

FORMATIONS = [full_grid, v_shape, diamond, pillars, checkerboard, hollow_box]

def random_formation(cols, rows):
    """Pick a random formation and return (cells, name)."""
    formation_func = random.choice(FORMATIONS)
    cells = formation_func(cols, rows)

    # Guard against a degenerate/empty result on very small grids.
    if not cells:
        return full_grid(cols, rows), 'full_grid'
    return cells, formation_func.__name__
