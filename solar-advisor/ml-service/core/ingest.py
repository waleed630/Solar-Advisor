"""Add a user's bill to the training data (only with consent), after checking it, then retrain."""
import csv
from datetime import date

from .data import DATA
from .train import retrain

MIN_MONTHS = 6


def usable_months(meter):
    """Months that look like real use. An empty house, a meter change or a misread photo gives a tiny number:
    that one month is left out, the rest of the bill is still used."""
    return {int(m): u for m, u in meter["months"].items() if u is not None and 10 <= u <= 20000}


def validate(meters):
    problems = []
    for i, meter in enumerate(meters, 1):
        good = usable_months(meter)
        if len(good) < MIN_MONTHS:
            problems.append(f"meter {i}: only {len(good)} usable months (need {MIN_MONTHS})")
    return problems


def next_site_id():
    with open(DATA / "houses.csv", newline="") as f:
        ids = [r["site_id"] for r in csv.DictReader(f) if r["site_id"].startswith("U")]
    return f"U{len(ids) + 1:03d}"


def month_totals(meters):
    """All meters added up: {month: units}."""
    total = {}
    for meter in meters:
        for m, u in usable_months(meter).items():
            total[m] = total.get(m, 0) + round(u)
    return total


SAME_HOME_SHARE = 0.75   # this share of the new bill's months matching one home = the same home again
SAME_HOME_MIN = 6        # ...and at least this many months


def known_homes():
    """site -> month -> every total seen for that month (any year), all meters added."""
    totals = {}
    with open(DATA / "bills.csv", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["site_id"], int(r["year"]), int(r["month"]))
            totals[key] = totals.get(key, 0) + int(float(r["units"]))
    homes = {}
    for (site, _, month), units in totals.items():
        homes.setdefault(site, {}).setdefault(month, set()).add(units)
    return homes


def matching_home(meters, homes=None):
    """The site id of a home already in the data that this bill comes from, or None.

    Not only the exact same bill: a bill read from a photo with a misread month, a bill with a month typed
    differently, or the next month's bill of the same home (11 of its 12 months are the same) all count.
    Two different homes almost never have the same units in 9 of 12 months.
    """
    new = month_totals(meters)
    if not new:
        return None
    homes = known_homes() if homes is None else homes
    for site, h in homes.items():
        same = sum(1 for m, u in new.items() if u in h.get(m, ()))
        if same >= SAME_HOME_MIN and same >= SAME_HOME_SHARE * len(new):
            return site
    return None


def already_in_data(meters):
    """True if this home's bill has already been used for training."""
    return matching_home(meters) is not None


def add_bill(meters, house, submission_id=""):
    problems = validate(meters)
    if problems:
        return {"added": False, "reason": "; ".join(problems)}
    if not house.get("sanctioned_load_kw"):
        return {"added": False, "reason": "sanctioned load missing"}
    if already_in_data(meters):
        return {"added": False, "reason": "this home's bill is already in the training data, so it was not added again"}

    site = next_site_id()
    today = date.today()
    with open(DATA / "bills.csv", "a", newline="") as f:
        w = csv.writer(f)
        for i, meter in enumerate(meters, 1):
            for m, u in sorted(usable_months(meter).items()):
                year = today.year if m <= today.month else today.year - 1   # last 12 bill months
                w.writerow([f"B{site}", site, f"{site}-M{i}", "PK", "Lahore", "residential", m, year, round(u),
                            round(house["sanctioned_load_kw"] / len(meters), 2), "", ""])

    with open(DATA / "houses.csv", newline="") as f:
        header = next(csv.reader(f))
    a = house.get("appliances") or {}
    count = lambda *keys: sum(a.get(k) or 0 for k in keys) or ""
    row = dict.fromkeys(header, "")
    row.update(site_id=site, building_id=f"B{site}", house_size_marla=house.get("house_size_marla") or "",
               people=house.get("people") or "", ac_total=house.get("ac_total") or "",
               ac_inverter=count("ac_inverter", "ac_1ton_inverter"),
               ac_noninverter=count("ac_noninverter", "ac_1ton_noninverter"),
               fans_total=count("fans", "fans_inverter"), fans_inverter=count("fans_inverter"),
               fridge_total=count("fridge", "fridge_inverter"), fridge_inverter=count("fridge_inverter"),
               motor=count("motor"), geyser_electric=count("geyser"), water_dispenser=count("water_dispenser"),
               electric_stove=count("electric_stove"), iron=count("iron"), led_tv=count("led_tv"),
               ups=count("ups"), air_cooler=count("air_cooler"),
               meters_total=len(meters), meters_with_bills=len(meters), has_solar=0,
               notes=f"added from app with consent, submission {submission_id}")
    with open(DATA / "houses.csv", "a", newline="") as f:
        csv.DictWriter(f, fieldnames=header).writerow(row)

    # The bill is saved either way; a failed retrain must not hide that (the next retrain picks it up)
    try:
        result = retrain()
    except Exception as e:  # noqa: BLE001 - report any training error back instead of a 500
        result = {"error": f"retrain failed: {e}"}
    return {"added": True, "site_id": site, "retrain": result}
