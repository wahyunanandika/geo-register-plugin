# Geoid Data

## egm96-5.pgm

**Source:** [NGA EGM96 geoid model](http://earth-info.nga.mil/GandG/wgs84/gravitymod/egm96/egm96.html),
distributed by the [GeographicLib project](https://geographiclib.sourceforge.io/).

**Download:**
```
https://downloads.sourceforge.net/project/geographiclib/geoids-distrib/egm96-5.tar.bz2
```

**Format:** GeographicLib binary PGM — 5-arcminute grid (4320 × 2161 cells),
16-bit big-endian unsigned integers.
Header metadata (`Offset`, `Scale`) converts raw values to geoid undulation in metres.

**Coverage:** Global (90°S – 90°N, 0°E – 360°E).

**Accuracy:** ±0.14 m max bilinear error, ±0.005 m RMS (per file header).

**Licence:** Public domain (US Government work, NGA).

**Used by:** `geo/geoid.py` — converts MSL altitude from EXIF GPS tags to
WGS-84 ellipsoidal height before passing to `geodetic_to_ecef`.
