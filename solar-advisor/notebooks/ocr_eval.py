"""Check the bill OCR against the hand-entered bills (our answer key). Run: ml-service/venv/Scripts/python notebooks/ocr_eval.py IMAGE_FOLDER"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "ml-service"))
from core.ocr import read_bill  # noqa: E402

PHOTOS = {"1.jpg": "H001-M1", "2.jpg": "H003-M1", "6.jpg": "H004-M1",
          "11.jpg": "H005-M1", "12.jpg": "H006-M1", "13.jpg": "H007-M1"}

folder = Path(sys.argv[1])
bills = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "bills.csv")
right = total = 0
for photo, meter in PHOTOS.items():
    b = bills[bills.meter_id == meter].sort_values(["year", "month"]).iloc[:-1].tail(12)  # history table only
    truth = {int(r.month): int(r.units) for r in b.itertuples()}
    got = read_bill((folder / photo).read_bytes())["months"]
    ok = sum(got.get(m) == u for m, u in truth.items())
    right, total = right + ok, total + len(truth)
    print(f"{photo:7} {meter}: {ok:2}/{len(truth)} right, {len(got)} found")
print(f"TOTAL {right}/{total} = {100 * right / total:.0f}%")
