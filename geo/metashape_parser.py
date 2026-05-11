"""Parse Agisoft Metashape camera XML exports."""
from pathlib import Path


class MetashapeXMLError(Exception):
    pass


def parse_metashape_xml(path: str) -> list[dict]:
    """Return [{name, lat, lon, alt}, ...] from a Metashape camera XML file.

    All enabled chunks with a GEOGCS (EPSG:4326) CRS are merged into a single
    list. Chunks with a non-GEOGCS CRS are skipped with a warning. Raises
    MetashapeXMLError if no usable chunk is found.

    For GEOGCS chunks, camera <reference> x/y/z are lon/lat/alt (WGS-84).
    Cameras without a <reference> tag or with enabled="0" are skipped.
    """
    import logging
    import xml.etree.ElementTree as ET

    log = logging.getLogger("geo_register")

    tree = ET.parse(path)
    root = tree.getroot()

    # Support bare <chunk> root (single-chunk export) or <document> root.
    if root.tag == "chunk":
        chunks = [root]
    else:
        chunks = [c for c in root.findall("chunk") if c.get("enabled", "1") != "0"]

    if not chunks:
        raise MetashapeXMLError("No <chunk> element found in Metashape XML.")

    gps_list: list[dict] = []
    skipped_chunks: list[str] = []
    total_cameras_seen = 0

    for chunk in chunks:
        chunk_label = chunk.get("label", "<unnamed>")

        chunk_ref = chunk.find("reference")
        if chunk_ref is None or not (chunk_ref.text or "").strip():
            skipped_chunks.append(f"'{chunk_label}' (no CRS reference)")
            continue

        wkt = chunk_ref.text.strip()
        if not wkt.startswith("GEOGCS"):
            crs_preview = wkt[:40].replace("\n", " ")
            skipped_chunks.append(f"'{chunk_label}' (CRS: {crs_preview}...)")
            continue

        cameras_elem = chunk.find("cameras")
        if cameras_elem is None:
            skipped_chunks.append(f"'{chunk_label}' (no <cameras> element)")
            continue

        # For GEOGCS chunks, camera <reference> x/y/z are lon/lat/alt (WGS-84).
        before = len(gps_list)
        chunk_cameras = 0
        for camera in cameras_elem.findall("camera"):
            label = camera.get("label", "")
            if not label:
                continue
            chunk_cameras += 1

            ref = camera.find("reference")
            if ref is None:
                continue
            if ref.get("enabled", "1") == "0":
                continue

            x_str = ref.get("x")
            y_str = ref.get("y")
            z_str = ref.get("z")
            if x_str is None or y_str is None or z_str is None:
                continue

            gps_list.append({
                "name": Path(label).stem,
                "lat": float(y_str),
                "lon": float(x_str),
                "alt": float(z_str),
            })

        added = len(gps_list) - before
        total_cameras_seen += chunk_cameras
        log.info(
            "geo_register: chunk '%s' — %d / %d camera(s) have GPS reference.",
            chunk_label, added, chunk_cameras,
        )

    if skipped_chunks:
        log.warning(
            "geo_register: skipped %d chunk(s) with unsupported CRS "
            "(re-export with WGS84/EPSG:4326): %s",
            len(skipped_chunks), ", ".join(skipped_chunks),
        )

    if not gps_list:
        if skipped_chunks and total_cameras_seen == 0:
            raise MetashapeXMLError(
                f"No usable chunk found (skipped {len(skipped_chunks)} chunk(s) with "
                "unsupported CRS). Re-export from Metashape with the chunk CRS set to "
                "WGS84 (EPSG:4326)."
            )
        raise MetashapeXMLError(
            f"Found {total_cameras_seen} camera(s) across "
            f"{len(chunks) - len(skipped_chunks)} chunk(s), but none have GPS "
            "reference data. In Metashape, assign camera reference coordinates in "
            "the Reference pane before exporting the XML."
        )

    return gps_list
