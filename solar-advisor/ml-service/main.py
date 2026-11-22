"""SolarAdvisor ML service (FastAPI, port 8000).

Run:  venv\\Scripts\\activate  then  uvicorn main:app --reload --port 8000
"""
import json
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core.appliances import APPLIANCES, breakdown
from core.data import CONFIG, MODELS, SEASON_OF
from core.predict import year_from_bill, year_from_house
from core.solar import STRUCTURES, plan
from core.train import current_meta, load_seasonal, retrain

app = FastAPI(title="SolarAdvisor ML service")


def default_config():
    return json.loads((CONFIG / "pakistan.json").read_text())


class Meter(BaseModel):
    months: dict[int, Optional[float]] = Field(description="bill month (1-12) -> units")


class House(BaseModel):
    house_size_marla: Optional[float] = None
    people: Optional[int] = None
    ac_total: Optional[int] = None
    sanctioned_load_kw: Optional[float] = None
    appliances: dict[str, int] = {}


class Roof(BaseModel):
    type: str = "concrete"
    area_sqft: Optional[float] = None


class PlanRequest(BaseModel):
    meters: list[Meter] = []
    house: House = House()
    roof: Roof = Roof()
    config: Optional[dict] = None   # prices/tariff from the database; defaults to config/pakistan.json


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/config/default")
def config_default():
    return default_config()


@app.get("/options")
def options():
    return {"appliances": {k: v[0] for k, v in APPLIANCES.items()},
            "roof_types": {k: v["name"] for k, v in STRUCTURES.items()}}


@app.get("/model")
def model_info():
    history = MODELS / "history.csv"
    return {"seasonal": load_seasonal(), "house_model": current_meta(),
            "history": pd.read_csv(history).fillna("").to_dict("records") if history.exists() else []}


@app.post("/retrain")
def retrain_now(drop_outliers: bool = False):
    return retrain(drop_outliers=drop_outliers)


@app.post("/plan")
def make_plan(req: PlanRequest):
    cfg = req.config or default_config()

    # 1. Twelve months of units: add up all meters, fill missing months with the model
    total = {m: 0.0 for m in range(1, 13)}
    known = set()
    for meter in req.meters:
        for m, u in meter.months.items():
            if u is not None and u > 0:
                total[int(m)] += u
                known.add(int(m))
    if known:
        year, house_mean = year_from_bill({m: total[m] for m in known})
        basis = "bill"
    else:
        details = req.house.model_dump()
        if not details.get("sanctioned_load_kw"):
            raise HTTPException(400, "Give at least one month of units, or the sanctioned load")
        year = year_from_house(details)
        house_mean = round(sum(v["units"] for v in year.values()) / 12)
        basis = "house details"
    year_units = {m: v["units"] for m, v in year.items()}

    # 2. Summer / winter / mild averages
    seasons = {}
    for s in ("summer", "winter", "mild"):
        vals = [year_units[m] for m in range(1, 13) if SEASON_OF[m] == s]
        seasons[s] = {"avg_per_month": round(sum(vals) / len(vals)), "total": round(sum(vals))}

    # 3. Solar size, cost, savings, payback
    result = plan(year_units, req.roof.area_sqft, req.roof.type, req.house.sanctioned_load_kw, cfg)

    # 4. Appliance breakdown
    apps = breakdown(req.house.appliances, {s: v["avg_per_month"] for s, v in seasons.items()}) if req.house.appliances else {}

    seasonal = load_seasonal()
    house_meta = current_meta() or {}
    return {
        "basis": basis,
        "months": year,
        "house_mean": house_mean,
        "seasons": seasons,
        "plan": result,
        "appliances": apps,
        "buyback_rate": cfg["net_billing"]["buyback_rate_per_unit"],
        "model": {"based_on_houses": seasonal["n_houses"],
                  "seasonal_mae": seasonal["mae"], "seasonal_r2": seasonal["r2"],
                  "house_model": house_meta.get("model"), "house_model_r2": house_meta.get("r2")},
    }


class AddBillRequest(BaseModel):
    meters: list[Meter]
    house: House
    submission_id: str = ""


@app.post("/bills/add")
def add_bill_route(req: AddBillRequest):
    from core.ingest import add_bill
    return add_bill([m.model_dump() for m in req.meters], req.house.model_dump(), req.submission_id)


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    from core.ocr import read_bill
    from core.ocr_claude import enabled as claude_enabled, read_bill_claude
    data = await file.read()
    try:
        if claude_enabled():
            return read_bill_claude(data)
        return {**read_bill(data), "engine": "tesseract"}
    except RuntimeError as e:
        raise HTTPException(503, str(e))
