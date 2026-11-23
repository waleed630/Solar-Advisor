"""Tests for the ML service core. Run from ml-service/:  venv\\Scripts\\python -m pytest -q"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.appliances import breakdown, items_from_counts, profile  # noqa: E402
from core.data import CONFIG, build_clean  # noqa: E402
from core.ingest import already_in_data, validate  # noqa: E402
from core.predict import year_from_bill  # noqa: E402
from core.solar import plan, system_cost  # noqa: E402
from core.tariff import energy_charge, monthly_bill, status_for  # noqa: E402

CFG = json.loads((CONFIG / "pakistan.json").read_text())
T = CFG["tariff_residential"]
ZAIN = {11: 129, 12: 87, 1: 79, 2: 78, 3: 116, 4: 161, 5: 287, 6: 291, 7: 335, 8: 372, 9: 342, 10: 271}


# ---------- data rules ----------

def test_clean_data_keeps_only_homes_without_solar_and_with_all_meters():
    clean = build_clean()
    homes = set(clean["site_id"])
    assert not homes & {"H001", "H002", "H003"}            # H002/H003 solar, H001 missing a meter
    assert {"H004", "H005", "H006", "H007"} <= homes       # clean homes are always in (new homes may be added)
    assert (clean["units"] >= 10).all()


def test_outlier_can_be_dropped():
    assert len(build_clean(drop_outliers=True)) == len(build_clean()) - 1


# ---------- tariff ----------

def test_protected_slabs_are_stepped():
    # 100 units at the first rate + 11 at the second
    assert energy_charge(111, "protected", T) == pytest.approx(100 * 10.54 + 11 * 13.01)


def test_unprotected_charges_every_unit_at_the_month_slab():
    assert energy_charge(271, "unprotected", T) == pytest.approx(271 * 33.10)


def test_status():
    assert status_for([150, 180, 199], 2, T) == "protected"
    assert status_for([150, 201], 2, T) == "unprotected"
    assert status_for([150], 9, T) == "tou"


def test_bill_estimate_close_to_a_real_bill():
    real = 13264                         # Zain's October 2026 bill, 271 units
    est = monthly_bill(271, "unprotected", T)
    assert abs(est - real) / real < 0.15


# ---------- prediction ----------

def test_full_bill_is_kept_as_is():
    year, _ = year_from_bill(ZAIN)
    assert all(year[m]["units"] == u and year[m]["source"] == "bill" for m, u in ZAIN.items())


def test_missing_months_are_filled_and_summer_is_higher():
    year, _ = year_from_bill({8: 372, 9: 342, 10: 271})
    assert len(year) == 12
    assert year[6]["source"] == "model"
    assert year[6]["units"] > year[1]["units"]


# ---------- solar plan ----------

def test_small_systems_still_pay_for_a_whole_inverter():
    cost, parts = system_cost(0.585, 0, "concrete", CFG)
    assert parts["inverter"] == CFG["prices"]["min_inverter_kw"]["value"] * CFG["prices"]["inverter_ongrid_per_kw"]["value"]


def test_plan_is_sensible_for_a_real_home():
    p = plan(ZAIN, 900, "concrete", 2, CFG)
    rec = p["recommended"]
    assert rec["panels"] >= 2
    assert 1 < rec["payback_years"] < 10
    assert p["roof"]["fits"]
    assert p["with_battery"]["cost"] > rec["cost"]


def test_small_roof_limits_the_size():
    p = plan(ZAIN, 160, "concrete", 2, CFG)            # room for about 2 kW
    assert p["recommended"]["kw"] <= 160 / CFG["solar"]["roof_sqft_per_kw"] + 0.01


# ---------- adding user bills ----------

def test_validation_rejects_short_or_strange_bills():
    assert validate([{"months": {1: 100, 2: 90}}])                                   # too few months
    assert validate([{"months": {m: 5 for m in range(1, 13)}}])                      # near zero
    assert not validate([{"months": {m: 200 for m in range(1, 13)}}])


def test_one_odd_month_does_not_throw_away_the_bill():
    from core.ingest import usable_months
    bill = {"months": {**{m: 200 for m in range(1, 13)}, 3: 9, 12: 4}}             # empty-house month, misread month
    assert not validate([bill])
    assert 3 not in usable_months(bill) and 12 not in usable_months(bill) and len(usable_months(bill)) == 10


def test_defective_or_changed_meter_months_are_left_out():
    from core.data import build_monthly, ESTIMATED_STATUS
    assert ESTIMATED_STATUS == {"DF", "MC"}
    assert "estimated" in build_monthly().columns


# ---------- bill reading (OCR text parsing) ----------

def test_barcode_line_does_not_replace_the_table():
    from core.ocr import parse
    text = """BILL HISTORY
    OCT25 157 5700 5700   APR26 68 1435 1435
    NOV25 51 1422 1422    MAY26 181 3401 3401
    OCT 26 - 10416794 - 08113460594715U - 000007169 - 06 NOV 26 - 000007456"""
    got = parse(text)
    assert got[10] == (157, 2025) and got[11] == (51, 2025)


def test_unread_units_are_left_empty_not_wrong():
    from core.ocr import plausible_units
    assert plausible_units([3018, 3018]) is None      # bill and payment: the units were not read
    assert plausible_units([6, 3018]) is None         # "96" lost a digit
    assert plausible_units([96, 3018]) == 96
    assert plausible_units([2, 477]) == 2             # tiny use, mostly fixed charges: real
    assert plausible_units([1595, 222730]) == 1595    # big bill with old arrears: real


def test_house_model_trains_when_some_details_are_blank():
    import numpy as np
    from core.train import MEDIUM_FEATURES, make_model
    df = build_clean().copy()
    df.loc[df.index[:5], "ac_total"] = np.nan          # like a bill sent from the app with AC left blank
    fit_df = df.dropna(subset=MEDIUM_FEATURES + ["units"])
    make_model("Ridge").fit(fit_df[MEDIUM_FEATURES], fit_df["units"])   # must not raise


def test_same_home_is_recognised_even_when_not_identical():
    from core.ingest import matching_home
    h006 = {10: 157, 11: 51, 12: 35, 1: 79, 2: 24, 3: 51, 4: 68, 5: 181, 6: 425, 7: 419, 8: 248, 9: 324}
    assert matching_home([{"months": {**h006, 10: 50, 11: 100}}]) == "H006"            # two months typed differently
    assert matching_home([{"months": {**ZAIN, 10: 140}}]) == "H007"                    # next month's bill
    assert matching_home([{"months": {m: 1000 + m for m in range(1, 13)}}]) is None   # a new home


def test_homes_in_the_data_do_not_look_like_each_other():
    from core.ingest import known_homes, matching_home
    homes = known_homes()
    for site, h in homes.items():
        latest = {m: max(v) for m, v in h.items()}
        assert matching_home([{"months": latest}], {s: v for s, v in homes.items() if s != site}) is None


def test_same_bill_twice_is_detected():
    assert already_in_data([{"months": ZAIN}])
    assert not already_in_data([{"months": {m: 12345 for m in range(1, 13)}}])


# ---------- appliances ----------

SEASONS = {"summer": 300, "winter": 100, "mild": 180}


def test_unknown_appliance_is_kept_with_a_guessed_power():
    out = breakdown([{"key": "custom", "label": "air fryer", "count": 1}, {"key": "fans", "count": 2}], SEASONS)
    names = {i["appliance"]: i for i in out["summer"]["items"]}
    assert names["Air fryer"]["how"] == "guessed"
    assert names["Ceiling fan"]["how"] == "typical"


def test_users_watts_and_hours_replace_the_typical_figures():
    label, watts, hours, how = profile({"key": "fans", "watts": 50, "hours": 6})
    assert (watts, hours["summer"], how) == (50, 6, "yours")
    assert hours["winter"] == 0                      # fans still off in winter: the pattern is kept


def test_a_2_ton_ac_draws_more_than_a_1_5_ton_one():
    _, w15, _, _ = profile({"key": "ac_noninverter"})
    label, w2, _, _ = profile({"key": "ac_noninverter", "ton": 2})
    assert w2 > w15 and "2 ton" in label


def test_old_count_format_still_works():
    out = breakdown(items_from_counts({"fans": 3, "fridge": 1}), SEASONS)
    assert out["summer"]["bill_units"] == 300
    assert sum(i["share_percent"] for i in out["summer"]["items"]) in range(99, 102)
