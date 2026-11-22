"""Measure the models' accuracy and save it, so a later run can be compared with this one in the same way.

Save a snapshot:
    ml-service/venv/Scripts/python notebooks/accuracy_snapshot.py save NAME [--exclude U001,U002]
Compare two snapshots:
    ml-service/venv/Scripts/python notebooks/accuracy_snapshot.py compare OLD_NAME NEW_NAME

Every number is measured on homes the model has NOT seen (leave one home out), the same way every time.
"""
import argparse
import itertools
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "ml-service"))
from core.data import build_clean  # noqa: E402
from core.train import SEASONAL_BASE_TEMPS, candidates_for, evaluate, evaluate_seasonal  # noqa: E402

OUT = ROOT / "models" / "snapshots"


def measure(exclude):
    df = build_clean()
    if exclude:
        df = df[~df["site_id"].isin(exclude)]
    homes = sorted(df["site_id"].unique())

    # 1. Seasonal model (used when the user gives a bill): every shape tried, best one kept
    shapes = {str(b): evaluate_seasonal(df, b) for b in SEASONAL_BASE_TEMPS}
    best_key = min(shapes, key=lambda k: shapes[k]["mae"])
    best = shapes[best_key]

    # 2. House model (used without a bill): the recipe retrain() would pick for this many homes
    house = {}
    for name, feats in candidates_for(len(homes)):
        r = evaluate(name, feats, df)
        house[name] = {"features": feats, "mae": r["mae"], "r2": r["r2"]}
    house_best = min(house, key=lambda k: house[k]["mae"])

    # 3. Learning curve: average over groups of k homes (at most 30 random groups per size, fixed seed)
    rng = random.Random(0)
    curve = {}
    for k in range(2, len(homes) + 1):
        groups = list(itertools.combinations(homes, k))
        if len(groups) > 30:
            groups = rng.sample(groups, 30)
        runs = [evaluate_seasonal(df[df["site_id"].isin(g)], best["base_temp"]) for g in groups]
        curve[k] = {"error_percent": round(100 * sum(r["mape"] for r in runs) / len(runs), 1),
                    "r2": round(sum(r["r2"] for r in runs) / len(runs), 3), "groups": len(runs)}

    return {
        "date": date.today().isoformat(),
        "homes": homes, "n_homes": len(homes), "n_months": int(len(df)), "excluded": exclude,
        "seasonal": {"base_temp": best["base_temp"], "mae": best["mae"], "r2": best["r2"],
                     "error_percent": round(100 * best["mape"], 1), "mae_per_home": best["mae_per_house"],
                     "all_shapes_mae": {k: v["mae"] for k, v in shapes.items()}},
        "house_model": {"model": house_best, **house[house_best]},
        "learning_curve": curve,
    }


def save(name, exclude, ocr_note):
    snap = measure(exclude)
    if ocr_note:
        snap["ocr"] = ocr_note
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(snap, indent=2))
    s, h = snap["seasonal"], snap["house_model"]
    print(f"Saved {path.relative_to(ROOT)}")
    print(f"  homes {snap['n_homes']} ({', '.join(snap['homes'])}), months {snap['n_months']}")
    print(f"  seasonal model (with a bill): R2 {s['r2']}, error {s['mae']} units ({s['error_percent']}%), base {s['base_temp']} C")
    print(f"  house model (no bill): {h['model']}, R2 {h['r2']}, error {h['mae']} units")


def compare(old_name, new_name):
    old = json.loads((OUT / f"{old_name}.json").read_text())
    new = json.loads((OUT / f"{new_name}.json").read_text())
    rows = [
        ("Homes", old["n_homes"], new["n_homes"], "more"),
        ("Bill-months", old["n_months"], new["n_months"], "more"),
        ("With a bill: R2 (1 = perfect)", old["seasonal"]["r2"], new["seasonal"]["r2"], "more"),
        ("With a bill: average error (units/month)", old["seasonal"]["mae"], new["seasonal"]["mae"], "less"),
        ("With a bill: average error (%)", old["seasonal"]["error_percent"], new["seasonal"]["error_percent"], "less"),
        ("Without a bill: R2", old["house_model"]["r2"], new["house_model"]["r2"], "more"),
        ("Without a bill: average error (units/month)", old["house_model"]["mae"], new["house_model"]["mae"], "less"),
    ]
    print(f"{'':45} {old_name:>14} {new_name:>14}   better?")
    for label, a, b, good in rows:
        better = (b > a) if good == "more" else (b < a)
        print(f"{label:45} {a:>14} {b:>14}   {'yes' if better else ('same' if a == b else 'no')}")
    print(f"\nModel types: {old['house_model']['model']} -> {new['house_model']['model']}; "
          f"seasonal base {old['seasonal']['base_temp']} C -> {new['seasonal']['base_temp']} C")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save")
    s.add_argument("name")
    s.add_argument("--exclude", default="", help="comma-separated site ids to leave out, e.g. test copies")
    s.add_argument("--ocr", default="", help="OCR result to record with the snapshot (text)")
    c = sub.add_parser("compare")
    c.add_argument("old")
    c.add_argument("new")
    a = ap.parse_args()
    if a.cmd == "save":
        save(a.name, [x for x in a.exclude.split(",") if x], a.ocr)
    else:
        compare(a.old, a.new)
