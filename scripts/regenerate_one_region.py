"""Regenerate one known region's encroaching-buildings data (see regenerate_known_regions.py
for why this reuses predict_region() rather than notebook 03's loop). Run one region per
process invocation -- on memory-constrained machines, three regions in a single long-lived
process can accumulate enough peak RSS to get killed by a low-memory guard; a fresh process
per region guarantees everything is released back to the OS in between.

Usage:
    python scripts/regenerate_one_region.py Kasarani 36.8969 -1.2296
"""

import json
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import pipeline as p

EE_PROJECT = "solar-haven-349708"
WATERWAYS_PATH = "data/raw/kenya_osm/gis_osm_waterways_free_1.shp"


def main():
    region, lon, lat = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])

    ee.Initialize(project=EE_PROJECT)
    rf_model = p.load_rf_model()

    _, summary = p.predict_region(
        region,
        (lon, lat),
        waterways_path=WATERWAYS_PATH,
        rf_model=rf_model,
    )
    summary["calibrated_against_ground_truth"] = region == "Kasarani"
    print(json.dumps(summary))

    out_path = Path(p.DATA_DIR) / f"{region.lower()}_summary.json"
    out_path.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
