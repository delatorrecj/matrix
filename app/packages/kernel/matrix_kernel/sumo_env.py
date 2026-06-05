"""Locate the bundled eclipse-sumo install so `import sumolib`/`import traci` work.

The `eclipse-sumo` wheel (a kernel dependency) ships the SUMO binaries **and** the
Python tools (`sumolib`, `traci`) under the installed `sumo` package's `SUMO_HOME`,
*not* at site-packages top level. So a bare `import sumolib` fails until we add
`$SUMO_HOME/tools` to `sys.path`. Importing this module does that wiring as a side
effect, so kernel modules can simply::

    from matrix_kernel import sumo_env          # wires the path
    import sumolib, traci                        # now importable
    sumo_bin = sumo_env.bin_path("sumo")         # the bundled binary for traci.start

`libsumo` (the faster in-process binding) is not shipped in this wheel; the runner
uses subprocess `traci` against `bin_path("sumo")`. `HAS_LIBSUMO` records whether the
faster path is available so a later optimization (RFC matrix-rfc-001, 90 s budget)
can prefer it without changing call sites.

Canonical refs: docs/build-matrix.md §3 (verify-live), docs/implementation-plan-critical-path.md S3/S5.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def sumo_home() -> str:
    """Resolve SUMO_HOME from the installed `sumo` package and wire `tools/` onto
    `sys.path`. Idempotent (cached). Raises a clear error if eclipse-sumo is absent.
    """
    try:
        import sumo  # provided by the eclipse-sumo wheel
    except ImportError as e:  # pragma: no cover - environment guard
        raise ImportError(
            "eclipse-sumo is not importable. Run `uv sync` in app/packages/kernel; "
            "the wheel provides sumolib/traci + the SUMO binaries under SUMO_HOME."
        ) from e

    home = getattr(sumo, "SUMO_HOME", None) or os.path.dirname(sumo.__file__)
    os.environ.setdefault("SUMO_HOME", home)
    tools = os.path.join(home, "tools")
    if os.path.isdir(tools) and tools not in sys.path:
        sys.path.insert(0, tools)
    return home


def bin_path(name: str) -> str:
    """Absolute path to a bundled SUMO binary (e.g. ``bin_path("sumo")``,
    ``bin_path("netconvert")``). Appends ``.exe`` on Windows.
    """
    exe = name + (".exe" if os.name == "nt" else "")
    return os.path.join(sumo_home(), "bin", exe)


# Wire the path on import so consumers can `import sumolib`/`import traci` directly.
sumo_home()

try:  # the fast in-process binding is optional; the runner falls back to traci
    import libsumo  # noqa: F401

    HAS_LIBSUMO = True
except ImportError:
    HAS_LIBSUMO = False
