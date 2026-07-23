import sys
from pathlib import Path

# The game modules are plain top-level scripts (no package), so pytest's
# default rootless import mode won't find them from inside tests/. Put the
# project root on sys.path once, here, for every test module to use.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
