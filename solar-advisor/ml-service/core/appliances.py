"""Split the bill across appliances.

Typical watts and hours per day (approximate, not measured). The split is scaled so it adds up to the
real bill, so it shows WHICH appliances matter, not exact numbers.
"""

# key: (label, watts, hours/day in summer, winter, mild)
APPLIANCES = {
    "ac_noninverter":  ("AC (non-inverter, 1.5 ton)", 1900, 8, 0, 2),
    "ac_inverter":     ("AC (inverter, 1.5 ton)", 1050, 8, 0, 2),
    "ac_1ton_noninverter": ("AC (non-inverter, 1 ton)", 1300, 8, 0, 2),
    "ac_1ton_inverter":    ("AC (inverter, 1 ton)", 700, 8, 0, 2),
    "fans":            ("Ceiling fan", 80, 12, 0, 6),
    "fans_inverter":   ("Ceiling fan (DC / inverter)", 35, 12, 0, 6),
    "fridge":          ("Refrigerator", 70, 24, 24, 24),          # average draw while cycling
    "fridge_inverter": ("Refrigerator (inverter)", 45, 24, 24, 24),
    "deep_freezer":    ("Deep freezer", 100, 24, 24, 24),
    "motor":           ("Water motor", 750, 1, 1, 1),
    "geyser":          ("Electric geyser", 2500, 0, 1.5, 0.5),
    "electric_stove":  ("Electric stove", 1800, 1, 1.5, 1),
    "microwave":       ("Microwave / oven", 1100, 0.3, 0.3, 0.3),
    "washing_machine": ("Washing machine", 500, 0.5, 0.5, 0.5),
    "water_dispenser": ("Water dispenser", 90, 24, 24, 24),
    "iron":            ("Iron", 1000, 0.3, 0.3, 0.3),
    "led_tv":          ("LED TV", 90, 5, 5, 5),
    "lights":          ("LED lights (each)", 12, 6, 7, 6),
    "air_cooler":      ("Air cooler", 200, 10, 0, 3),
    "ups":             ("UPS charging and losses", 60, 8, 6, 6),
    "room_heater":     ("Room heater", 1500, 0, 3, 0),
}

SEASON_INDEX = {"summer": 2, "winter": 3, "mild": 4}


def expected_units(counts, season, days=30):
    out = {}
    for key, n in counts.items():
        if key not in APPLIANCES or not n:
            continue
        label, watts, *_ = APPLIANCES[key]
        hours = APPLIANCES[key][SEASON_INDEX[season]]
        out[key] = {"label": label, "count": n, "units": n * watts * hours * days / 1000}
    return out


def breakdown(counts, season_avg_units):
    """season_avg_units: {"summer": avg units per month, "winter": ..., "mild": ...} from the bill."""
    result = {}
    for season, real in season_avg_units.items():
        exp = expected_units(counts, season)
        total = sum(v["units"] for v in exp.values())
        if not total or not real:
            continue
        scale = real / total
        items = sorted(({"appliance": v["label"], "count": v["count"],
                         "units": round(v["units"] * scale),
                         "share_percent": round(100 * v["units"] / total)} for v in exp.values()),
                       key=lambda x: -x["units"])
        result[season] = {"bill_units": round(real), "typical_units": round(total),
                          "scale": round(scale, 2), "items": items}
    return result
