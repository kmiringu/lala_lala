"""Local API backing the frontend dashboard.

Two kinds of endpoints:
- Read-only ones that serve the already-computed outputs for the known regions
  (Kasarani/Gatharaini/Motoine) straight off disk.
- POST /api/predict, which runs src.pipeline.predict_region() live via Earth Engine for a
  region the user picks on the map. That call takes on the order of a minute or more
  depending on building density in the AOI, so it's a plain `def` (not `async def`) --
  FastAPI runs sync endpoints in a thread pool, which keeps the read-only endpoints
  responsive while a prediction is in flight.

Run from the repo root:
    uvicorn app.main:app --reload
"""

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import pipeline as p

EE_PROJECT = "solar-haven-349708"
KNOWN_REGIONS = {"Kasarani", "Gatharaini", "Motoine"}
# pipeline.WATERWAYS_PATH points at data/vectors/, which is empty in this checkout —
# the shapefile actually lives under data/raw/kenya_osm/ here.
WATERWAYS_PATH = "data/raw/kenya_osm/gis_osm_waterways_free_1.shp"

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ee.Initialize(project=EE_PROJECT)
    state["rf_model"] = p.load_rf_model()
    yield


app = FastAPI(title="Riparian Encroachment API", lifespan=lifespan)

# Dev-only: the frontend is served separately (e.g. `python -m http.server` in web/),
# so it's a different origin from this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _buildings_geojson(region_key):
    csv_path = Path(p.DATA_DIR) / f"{region_key.lower()}_encroaching_buildings.csv"
    if not csv_path.exists():
        raise HTTPException(404, f"No encroaching-buildings data for {region_key!r} yet")
    df = pd.read_csv(csv_path)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row.lon, row.lat]},
                "properties": {
                    "confidence": row.confidence,
                    "rf_builtup_prob": row.rf_builtup_prob,
                    "distance_to_river_m": row.distance_to_river_m,
                },
            }
            for row in df.itertuples()
        ],
    }


def _rivers_geojson(region_key):
    path = Path(p.DATA_DIR) / f"{region_key.lower()}_rivers.geojson"
    if not path.exists():
        raise HTTPException(404, f"No river geometry for {region_key!r} yet")
    rivers = gpd.read_file(path).to_crs(epsg=4326)
    return json.loads(rivers.to_json())


@app.get("/api/regions")
def list_known_regions():
    summary_path = Path(p.DATA_DIR) / "known_regions_summary.json"
    if not summary_path.exists():
        raise HTTPException(404, "known_regions_summary.json not generated yet — run scripts/regenerate_known_regions.py")
    return json.loads(summary_path.read_text())


@app.get("/api/regions/{region_key}/buildings")
def region_buildings(region_key: str):
    return _buildings_geojson(region_key)


@app.get("/api/regions/{region_key}/rivers")
def region_rivers(region_key: str):
    return _rivers_geojson(region_key)


class PredictRequest(BaseModel):
    region_key: str
    lon: float
    lat: float
    radius_km: float = p.CASE_STUDY_RADIUS_KM


@app.post("/api/predict")
def predict(req: PredictRequest):
    if req.region_key in KNOWN_REGIONS:
        raise HTTPException(400, f"{req.region_key!r} is already a known region — use GET /api/regions instead")

    _, summary = p.predict_region(
        req.region_key,
        (req.lon, req.lat),
        radius_km=req.radius_km,
        rf_model=state["rf_model"],
        waterways_path=WATERWAYS_PATH,
    )
    return {
        "summary": summary,
        "buildings": _buildings_geojson(req.region_key),
        "rivers": _rivers_geojson(req.region_key),
    }
