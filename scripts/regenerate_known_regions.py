"""Regenerate the known-regions dataset (Kasarani/Gatharaini/Motoine) the frontend reads.

Uses the same inference path as any brand-new region (src/pipeline.predict_region) instead
of duplicating notebook 03's loop, so there's one codepath for "run the calibrated pipeline
on a region" regardless of whether that region is one of the original three or not.

Kasarani is the one region with an independent field count (Pamoja Trust, ~700) that Module 4
used to derive the 16m threshold in the first place -- everything else about running it here
is identical to a brand-new region, so we override calibrated_against_ground_truth for it
after the fact rather than teach predict_region() a special case it shouldn't have.

Run from the repo root:
    python scripts/regenerate_known_regions.py
"""

import json
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import pipeline as p

EE_PROJECT = "solar-haven-349708"

# Centers as resolved in 01_preprocessing.ipynb / 02_modelling.ipynb.
KNOWN_REGIONS = {
    "Kasarani": (36.8969, -1.2296),
    "Gatharaini": (36.95952127354356, -1.2252700532171976),
    "Motoine": (36.74237847877641, -1.3113205815273903),
}


def main():
    ee.Initialize(project=EE_PROJECT)
    rf_model = p.load_rf_model()

    summary = {}
    for region, center in KNOWN_REGIONS.items():
        print(f"--- {region} ---")
        _, region_summary = p.predict_region(
            region,
            center,
            waterways_path="data/raw/kenya_osm/gis_osm_waterways_free_1.shp",
            rf_model=rf_model,
        )
        region_summary["calibrated_against_ground_truth"] = region == "Kasarani"
        summary[region] = region_summary
        print(region_summary)

    out_path = f"{p.DATA_DIR}/known_regions_summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
