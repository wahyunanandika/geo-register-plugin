"""EGM96 geoid undulation lookup from a GeographicLib PGM file.

Provides MSL → WGS-84 ellipsoidal height conversion.
The PGM file (geo/data/egm96-5.pgm) is loaded once on first use.
"""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

_DATA_DIR  = Path(__file__).parent / "data"
_PGM_PATH  = _DATA_DIR / "egm96-5.pgm"

_grid: np.ndarray | None = None   # uint16, shape (2161, 4320)
_offset: float = 0.0
_scale:  float = 1.0
_lock = threading.Lock()


def _load() -> None:
    global _grid, _offset, _scale

    with open(_PGM_PATH, "rb") as f:
        # ── parse text header ─────────────────────────────────────────────
        while True:
            line = f.readline().decode("ascii", errors="ignore").strip()
            if line.startswith("# Offset"):
                _offset = float(line.split()[-1])
            elif line.startswith("# Scale"):
                _scale = float(line.split()[-1])
            elif line and not line.startswith("#") and not line.startswith("P"):
                # dimension line "4320 2161"
                cols, rows = map(int, line.split())
                break
        f.readline()   # maxval line (65535)

        # ── read binary grid (big-endian uint16) ──────────────────────────
        raw = np.frombuffer(f.read(), dtype=">u2")

    _grid = raw.reshape(rows, cols)   # (2161, 4320)


def _ensure_loaded() -> None:
    if _grid is None:
        with _lock:
            if _grid is None:
                _load()


def undulation(lat_deg: float | np.ndarray,
               lon_deg: float | np.ndarray) -> float | np.ndarray:
    """Return EGM96 geoid undulation N (metres) at the given WGS-84 lat/lon.

    N is defined so that:  h_ellipsoidal = h_MSL + N
    """
    _ensure_loaded()

    lat = np.asarray(lat_deg, dtype=np.float64)
    lon = np.asarray(lon_deg, dtype=np.float64) % 360.0   # normalise to [0, 360)

    # Grid: row 0 = 90°N, row 2160 = 90°S  →  step = 5 arcmin = 1/12°
    step = 5.0 / 60.0
    row_f = (90.0 - lat) / step
    col_f = lon / step

    r0 = np.clip(np.floor(row_f).astype(int), 0, _grid.shape[0] - 2)
    c0 = np.floor(col_f).astype(int) % _grid.shape[1]
    r1 = r0 + 1
    c1 = (c0 + 1) % _grid.shape[1]

    dr = row_f - r0
    dc = col_f - c0

    v00 = _grid[r0, c0].astype(np.float64)
    v01 = _grid[r0, c1].astype(np.float64)
    v10 = _grid[r1, c0].astype(np.float64)
    v11 = _grid[r1, c1].astype(np.float64)

    raw = ((1 - dr) * (1 - dc) * v00
           + (1 - dr) * dc      * v01
           + dr       * (1 - dc) * v10
           + dr       * dc       * v11)

    N = _offset + _scale * raw

    if N.ndim == 0:
        return float(N)
    return N


def msl_to_ellipsoidal(lat_deg: float | np.ndarray,
                       lon_deg: float | np.ndarray,
                       alt_msl: float | np.ndarray) -> float | np.ndarray:
    """Convert MSL altitude to WGS-84 ellipsoidal height.

    h_ellipsoidal = h_MSL + N(lat, lon)
    """
    return np.asarray(alt_msl, dtype=np.float64) + undulation(lat_deg, lon_deg)
