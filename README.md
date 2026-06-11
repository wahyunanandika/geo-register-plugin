# Geo Register Plugin

> **Status: Discontinued / Archived**
>
> Development on this fork has stopped. The georeferencing pipeline has been moved to a
> standalone repository that does not require LichtFeld Studio:
> **[wahyunanandika/georeference_3dtiles_gaussian_splatting](https://github.com/wahyunanandika/georeference_3dtiles_gaussian_splatting)**
>
> See [Why this fork is discontinued](#why-this-fork-is-discontinued) below.

---

Registers a [LichtFeld Studio](https://github.com/MrNeRF/LichtFeld-Studio/) scene to real-world geographic coordinates (WGS-84 / ECEF).
Once registered, clicking any point on the model returns its latitude, longitude, and altitude.
The plugin can also export geo-referenced splat models as **LAS/LAZ** point clouds or
**3D Tiles 1.1** datasets (ArcGIS Gaussian Splat Layer / CesiumJS).

![Geo Register Plugin in action](assets/plugin_example.jpg)

---

## Changes Made in This Fork

This fork started from [dozeri83/geo-register-plugin](https://github.com/dozeri83/geo-register-plugin)
with the goal of adding octree tiling and improving georeferencing accuracy.

### What was added

**Octree tiling** — the original plugin exports all splats as a single GLB tile.
For large scenes (5M+ splats) this causes Cesium to skip the tile entirely because
`geometricError` on a leaf node is too large to refine. This fork splits the scene
into an octree of hundreds of smaller tiles, each with correct `geometricError = bbox diagonal`.

**Bug fixes backported from dozeri83:**
- `geometricError` was multiplied by similarity scale factor (~12.79×) — removed
- `refine: "ADD"` changed to `refine: "REPLACE"` — ADD requires parent LOD splats which don't exist in single-level exports

### What was attempted but did not work

The main goal of this fork was to improve georeferencing accuracy beyond the original
plugin workflow. The original plugin estimates the similarity transform using camera
positions obtained through the LFS camera API, while Gaussian Splat PLY exports originate
from COLMAP reconstruction space.

During investigation, it became apparent that these coordinate spaces were not directly
equivalent for our workflow, and obtaining a consistent transform between them relied on
`node.world_transform` acting as the bridge between reconstruction-space coordinates and
the exported PLY.

Several approaches were explored:

| Approach | Result |
|---|---|
| XML scene-space positions (scale=12.79) | Correct RMSE=0.076m, alt=915m — but render failed in Cesium ion |
| LFS camera API with W from `node.world_transform` | W unavailable from PLY converter mode |
| Dump W via debug button | Requires cameras + splat loaded simultaneously — not possible in LFS |
| LFS v0.5.2 `world_transform_data_world` API | Could not be accessed reliably outside active export session |

LFS v0.5.2 (PR #1066) introduced a separation between `visualizer-world` and
`data-world` coordinate conventions. For our workflow, obtaining a consistent transform
between camera positions and exported PLY coordinates became increasingly difficult.

Additionally, LFS cannot simultaneously load COLMAP cameras and a Gaussian Splat PLY in
the mode required for this investigation, making validation of the transform chain difficult.

### Final state of this fork

Reverted `main_panel.py` and `metashape_parser.py` back to the dozeri83 approach
(LFS camera API, scale≈1.0). The octree tiling and bug fixes remain. This gives
correctly structured 3D Tiles that render in Cesium ion, but with the same
georeferencing accuracy as the original dozeri83 plugin.

For sub-meter georeferencing accuracy without LFS dependency, see the standalone
pipeline below.

---

## Why This Fork is Discontinued

After extensive testing and debugging, we concluded that the georeferencing challenges
encountered in this fork were primarily related to coordinate-space conversions between
reconstruction space, scene space, and ECEF coordinates.

For our workflow, obtaining a reliable and reproducible transform chain through LFS
internals proved difficult. Rather than continuing to depend on viewer-specific state,
development shifted toward a standalone pipeline that operates directly on source data.

The standalone workflow solves the similarity transform directly from COLMAP
`images.bin` camera centres to GPS ECEF references and therefore:

- Requires no running viewer
- Produces sub-meter accuracy on tested datasets (+0.27m offset vs terrain in Cesium ion)
- Is fully reproducible regardless of LFS version

**Standalone pipeline:**  
https://github.com/wahyunanandika/georeference_3dtiles_gaussian_splatting

---

## Original Documentation

The rest of this README is the original dozeri83 documentation, preserved for reference.

---

## How It Works

The plugin solves a **similarity transform** that maps scene-space coordinates to
ECEF (Earth-Centered Earth-Fixed) coordinates:

```
world_ecef = scale * R @ p_scene + translation
```

Where:
- `scale` — uniform scale factor between scene units and metres
- `R` — 3x3 rotation matrix
- `translation` — 3D translation vector in metres

The transform is estimated using a robust RANSAC + IRLS solver (Umeyama 1991),
which automatically rejects outlier correspondences.

---

## Source Modes

Use the **Source** dropdown to choose how geographic reference data is provided.

---

### 1. EXIF

Automatically extracts GPS coordinates embedded in the original drone/camera images,
matches them to the camera poses in the loaded scene, and solves the transform.

**Steps:**
1. Load your dataset in LichtFeld Studio.
2. Select **EXIF** from the Source dropdown.
3. Click **Calc Georeference From EXIF**.

The plugin scans the dataset folder for images with GPS EXIF tags, matches each image
to its camera pose by filename stem, and runs the solver.

> **Original images folder:**
> If your dataset images no longer contain GPS EXIF data (e.g. they were undistorted
> or re-encoded), click **Set Original Images Folder** to point the plugin at the
> folder containing your original images. The plugin will scan that folder for GPS
> tags instead.
> The filename **stem** (name without extension) must match between the original
> images and the dataset cameras — for example, `DJI_0001.jpg` (original) matches
> `DJI_0001.JPG` or `DJI_0001.png` in the dataset.

> **Note:** EXIF GPS readings can be imprecise, especially in the altitude direction. For more accurate results, use professional alignment tools with GCPs (ground control points).

---

### 2. Similarity File

Loads a previously computed similarity transform from a JSON file.

**Steps:**
1. Select **Similarity File** from the Source dropdown.
2. Click **Load Similarity File** and pick a `.json` file.

**Expected JSON format:**

```json
{
  "scale": 0.999367,
  "rotation": [
    [ 0.9998,  0.0123, -0.0156],
    [-0.0121,  0.9998,  0.0089],
    [ 0.0157, -0.0087,  0.9998]
  ],
  "translation": [4052845.12, 617312.45, 4867891.78]
}
```

---

### 3. Image Positions CSV

Loads image GPS positions from a CSV file and runs the same solver as the EXIF mode.

**Required CSV format:**

```
image_name,lat,lon,alt
DJI_0001.JPG,32.08154321,34.78912345,48.250
DJI_0002.JPG,32.08163897,34.78924561,48.431
```

---

### 4. RealityScan Parameters CSV

> **Recommended over EXIF when you aligned your data with RealityScan.**

**How to export from RealityScan:**

1. Go to **Workflow → Settings → Coordinate System** and set to **EPSG:4326 – GPS WGS 84**.
2. Export **Internal/External Camera Parameters** with coordinate system set to **Project Output**.

---

### 5. Metashape Cameras XML

Loads camera GPS positions from an Agisoft Metashape camera XML export.

**How to export from Metashape:**
1. Set chunk coordinate system to **WGS 84 (EPSG:4326)**.
2. Go to **File → Export → Export Cameras…** and save as XML.

---

## Output Files

After a successful solve the plugin writes to `<output_dir>/geo_register_plugin_data/`:

| File | Description |
|---|---|
| `similarity_transform.json` | The solved transform (scale, R, t, RMSE, inlier counts) |
| `similarity_transform_info.txt` | Human-readable explanation of the transform fields |
| `image_positions.csv` | GPS positions of all matched images |

---

## Export

### LAS / LAZ

LAS 1.4, point format 7 (XYZ + RGB). Output CRS controlled by `las_export_coordinates`
in `config.json` (`"UTM"` default or `"LLA"`).

### 3D Tiles

Exports 3D Tiles 1.1 with octree tiling (this fork) using
`KHR_gaussian_splatting` + `KHR_gaussian_splatting_compression_spz_2` (SPZ v3).

For production use, the standalone pipeline is recommended over this plugin.
