"""Region-agnostic inference pipeline: AOI in, encroaching structures out.

Extracted from `notebooks/01_preprocessing.ipynb`, `02_modelling.ipynb`, and
`03_fusion_and_report.ipynb`, which hardcode Kasarani/Gatharaini/Motoine in three
separate, duplicated `REGIONS`/`REGION_CENTERS` dicts. `predict_region()` below runs
the same steps for an arbitrary new region — river clip, structure detection, RF
scoring, river-distance fusion — without retraining or ESA WorldCover sampling: it
reuses the RF model already trained in Module 2 (`rf_baseline.joblib`) and the 16m
distance threshold already calibrated in Module 4 against Kasarani's Pamoja Trust
field survey (the only ground truth that exists so far).

A region produced this way is NOT field-validated — `calibrated_against_ground_truth`
is always False for anything that isn't Kasarani, same as Gatharaini/Motoine today.
"""

from concurrent.futures import ThreadPoolExecutor

import ee
import geopandas as gpd
import joblib
import pandas as pd
from shapely.geometry import Point, box

WATERWAYS_PATH = "data/vectors/gis_osm_waterways_free_1.shp"
DATA_DIR = "data/processed"
RF_MODEL_PATH = f"{DATA_DIR}/rf_baseline.joblib"

CASE_STUDY_RADIUS_KM = 3
BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]
FEATURE_COLS = BANDS + ["NDVI", "NDBI"]
SENTINEL_PIXEL_SIZE_M = 10

CALIBRATED_DISTANCE_M = 16  # from 03_fusion_and_report.ipynb, calibrated on Kasarani's ~700 Pamoja Trust count
CONFIDENCE_THRESHOLD = 0.7
MATERIAL_OVERLAP_THRESHOLD = 0.05


def get_region_aoi(center, radius_km=CASE_STUDY_RADIUS_KM):
    """A fixed-radius circle, approximated here as its bounding box just for clipping vectors."""
    lon, lat = center
    pad_deg = radius_km / 111.0
    return box(lon - pad_deg, lat - pad_deg, lon + pad_deg, lat + pad_deg)


def load_waterways(waterways_path=WATERWAYS_PATH):
    return gpd.read_file(waterways_path)


def clip_rivers_to_aoi(waterways, aoi):
    clipped = waterways[waterways.intersects(aoi)].copy()
    rivers_only = clipped[clipped["fclass"].isin(["river", "stream"])].copy()
    if rivers_only.empty:
        raise ValueError("No river/stream features intersect this AOI — check the AOI bounds.")
    return rivers_only


def save_river_lines(rivers_only, region_key, out_dir=DATA_DIR):
    rivers_metric = rivers_only.to_crs(epsg=32737)[["name", "fclass", "geometry"]]
    path = f"{out_dir}/{region_key.lower()}_rivers.geojson"
    rivers_metric.to_file(path, driver="GeoJSON")
    return path


def _mask_s2_clouds(image):
    scl = image.select("SCL")
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return image.updateMask(mask)


def get_sentinel2_feature_image(aoi_ee, start_date="2024-01-01", end_date="2024-12-31", cloud_threshold=20):
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi_ee)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
        .map(_mask_s2_clouds)
    )
    composite = s2.select(BANDS).median().clip(aoi_ee)
    ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndbi = composite.normalizedDifference(["B11", "B8"]).rename("NDBI")
    return composite.addBands(ndvi).addBands(ndbi)


def detect_structures_open_buildings(aoi_ee, confidence_threshold=CONFIDENCE_THRESHOLD, batch_size=4000, max_workers=6):
    fc = (
        ee.FeatureCollection("GOOGLE/Research/open-buildings/v3/polygons")
        .filterBounds(aoi_ee)
        .filter(ee.Filter.gte("confidence", confidence_threshold))
    )
    n = fc.size().getInfo()

    def fetch_batch(start):
        return ee.FeatureCollection(fc.toList(batch_size, start)).getInfo()["features"]

    starts = list(range(0, n, batch_size))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        batches = pool.map(fetch_batch, starts)

    rows = []
    for batch in batches:
        for f in batch:
            props = f["properties"]
            lon, lat = props["longitude_latitude"]["coordinates"]
            rows.append({
                "lon": lon,
                "lat": lat,
                "confidence": props["confidence"],
                "area_m2": props["area_in_meters"],
            })
    return pd.DataFrame(rows)


def detect_structures_yolo(aoi_ee, resolution_m):
    """Strategy B — placeholder behind the same interface. Not implemented: needs imagery
    finer than the building size it must resolve (see Module 2, Step 2's feasibility check).
    """
    raise NotImplementedError(
        "Needs imagery finer than the building size it must resolve — see Module 2, Step 2."
    )


def detect_structures(aoi_ee, resolution_m=SENTINEL_PIXEL_SIZE_M):
    """Two strategies share this interface, so picking one never means deleting the other's
    code. Open Buildings is the current default — Module 2, Step 2 found real buildings are
    smaller than a Sentinel-2 pixel, ruling out a custom pixel-based detector for now.
    """
    return detect_structures_open_buildings(aoi_ee)


def score_buildings(buildings_df, aoi_ee, rf_model, batch_size=4000, max_workers=6):
    feature_image = get_sentinel2_feature_image(aoi_ee)

    def sample_batch(start):
        chunk = buildings_df.iloc[start:start + batch_size]
        points_fc = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([row.lon, row.lat]), {"row_id": i})
            for i, row in chunk.iterrows()
        ])
        sampled = feature_image.sampleRegions(collection=points_fc, scale=10, geometries=False).getInfo()["features"]
        return pd.DataFrame([
            {"row_id": f["properties"]["row_id"], **{c: f["properties"].get(c) for c in FEATURE_COLS}}
            for f in sampled
        ]).set_index("row_id")

    starts = list(range(0, len(buildings_df), batch_size))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        scored_frames = list(pool.map(sample_batch, starts))
    sampled_all = pd.concat(scored_frames)
    merged = buildings_df.join(sampled_all, how="left")
    valid = merged.dropna(subset=FEATURE_COLS)
    merged.loc[valid.index, "rf_builtup_prob"] = rf_model.predict_proba(valid[FEATURE_COLS])[:, 1]
    return merged


def add_river_distance(buildings_df, region_key, data_dir=DATA_DIR):
    rivers = gpd.read_file(f"{data_dir}/{region_key.lower()}_rivers.geojson")  # already EPSG:32737
    river_union = rivers.union_all()

    points = gpd.GeoDataFrame(
        buildings_df.copy(),
        geometry=[Point(xy) for xy in zip(buildings_df["lon"], buildings_df["lat"])],
        crs="EPSG:4326",
    ).to_crs(epsg=32737)

    points["distance_to_river_m"] = points.geometry.distance(river_union)
    return pd.DataFrame(points.drop(columns="geometry"))


def filter_candidates(buildings_df, confidence_threshold=CONFIDENCE_THRESHOLD, material_threshold=MATERIAL_OVERLAP_THRESHOLD):
    mask = (
        (buildings_df["confidence"] >= confidence_threshold)
        & (buildings_df["rf_builtup_prob"] >= material_threshold)
    )
    return buildings_df[mask].copy()


def load_rf_model(path=RF_MODEL_PATH):
    return joblib.load(path)


def predict_region(
    region_key,
    center,
    radius_km=CASE_STUDY_RADIUS_KM,
    rf_model=None,
    waterways_path=WATERWAYS_PATH,
    out_dir=DATA_DIR,
    calibrated_distance_m=CALIBRATED_DISTANCE_M,
):
    """Run the trained, calibrated pipeline on a region that was not part of Module 1's
    original three. Inference only: no retraining, no WorldCover feature-table sampling.

    Requires `rf_baseline.joblib` (Module 2) to already exist, and needs `waterways_path`
    to point at the OSM waterways shapefile — neither is committed to git (both are
    gitignored / regenerated locally).

    Returns (encroaching_df, summary_dict). `summary_dict['calibrated_against_ground_truth']`
    is always False here — only Kasarani has an independent field count to calibrate against.
    """
    if rf_model is None:
        rf_model = load_rf_model()

    aoi = get_region_aoi(center, radius_km)
    aoi_ee = ee.Geometry.Point(list(center)).buffer(radius_km * 1000)

    waterways = load_waterways(waterways_path)
    rivers_only = clip_rivers_to_aoi(waterways, aoi)
    save_river_lines(rivers_only, region_key, out_dir)

    buildings_df = detect_structures(aoi_ee)
    scored = score_buildings(buildings_df, aoi_ee, rf_model)

    with_distance = add_river_distance(scored, region_key, out_dir)
    candidates = filter_candidates(with_distance)
    encroaching = candidates[candidates["distance_to_river_m"] <= calibrated_distance_m].copy()

    encroaching.to_csv(f"{out_dir}/{region_key.lower()}_encroaching_buildings.csv", index=False)

    summary = {
        "region": region_key,
        "buildings_screened": len(with_distance),
        "passed_confidence_and_material_filter": len(candidates),
        "encroaching_count": int(len(encroaching)),
        "calibrated_against_ground_truth": False,
        "calibrated_distance_m": calibrated_distance_m,
    }
    return encroaching, summary
