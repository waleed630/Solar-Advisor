"""Turn whatever the user gives us (a bill, some months, or only house details) into 12 months of units."""
import pandas as pd

from .data import load_weather, typical_month_weather
from .train import load_model, load_seasonal, seasonal_ratio

_TYPICAL = None


def typical_weather():
    global _TYPICAL
    if _TYPICAL is None:
        _TYPICAL = typical_month_weather(load_weather())
    return _TYPICAL


def ratio_for(month, seasonal):
    return float(seasonal_ratio(seasonal, [typical_weather()[month]["avg_temp"]])[0])


def year_from_bill(month_units):
    """month_units: {month (1-12): units} for the months we know. Fills the rest with the seasonal model.

    Each known month tells us the house's average: units / ratio(month).
    """
    seasonal = load_seasonal()
    known = {int(m): float(u) for m, u in month_units.items() if u is not None and float(u) > 0}
    if not known:
        raise ValueError("No months with units")
    house_mean = sum(u / ratio_for(m, seasonal) for m, u in known.items()) / len(known)
    year = {}
    for m in range(1, 13):
        if m in known:
            year[m] = {"units": round(known[m]), "source": "bill"}
        else:
            year[m] = {"units": round(house_mean * ratio_for(m, seasonal)), "source": "model"}
    return year, round(house_mean)


def year_from_house(details):
    """No bill: predict every month from house details with the house model."""
    model, meta = load_model()
    rows = []
    for m in range(1, 13):
        w = typical_weather()[m]
        row = {f: details.get(f) for f in meta["features"]}
        row.update({k: w[k] for k in ("avg_temp", "max_temp") if k in meta["features"]})
        rows.append(row)
    pred = model.predict(pd.DataFrame(rows)[meta["features"]])
    return {m: {"units": max(10, round(float(p))), "source": "house model"} for m, p in zip(range(1, 13), pred)}
