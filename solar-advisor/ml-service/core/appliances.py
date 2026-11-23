"""Split the bill across appliances.

Typical watts and hours per day (approximate, not measured). The split is scaled so it adds up to the
real bill, so it shows WHICH appliances matter, not exact numbers.

The user may also give an appliance's power (watts, kW, HP, amps, AC tons) and hours per day; those
replace the typical figures. Appliances we have no figures for ("custom") use a small default until
the user gives their power.
"""

# key: (label, watts, hours/day in summer, winter, mild)
APPLIANCES = {
    "ac_noninverter":  ("AC (non-inverter, 1.5 ton)", 1900, 8, 0, 2),
    "ac_inverter":     ("AC (inverter, 1.5 ton)", 1050, 8, 0, 2),
    "ac_1ton_noninverter": ("AC (non-inverter, 1 ton)", 1300, 8, 0, 2),
    "ac_1ton_inverter":    ("AC (inverter, 1 ton)", 700, 8, 0, 2),
    "fans":            ("Ceiling fan", 80, 12, 0, 6),
    "fans_inverter":   ("Ceiling fan (DC / inverter)", 35, 12, 0, 6),
    "exhaust_fan":     ("Exhaust fan", 40, 6, 3, 4),
    "fridge":          ("Refrigerator", 70, 24, 24, 24),          # average draw while cycling
    "fridge_inverter": ("Refrigerator (inverter)", 45, 24, 24, 24),
    "deep_freezer":    ("Deep freezer", 100, 24, 24, 24),
    "motor":           ("Water motor", 750, 1, 1, 1),
    "geyser":          ("Electric geyser", 2500, 0, 1.5, 0.5),
    "electric_stove":  ("Electric stove", 1800, 1, 1.5, 1),
    "microwave":       ("Microwave / oven", 1100, 0.3, 0.3, 0.3),
    "kettle":          ("Electric kettle", 1500, 0.2, 0.3, 0.2),
    "toaster":         ("Toaster / sandwich maker", 800, 0.2, 0.2, 0.2),
    "blender":         ("Blender / juicer", 400, 0.2, 0.2, 0.2),
    "washing_machine": ("Washing machine", 500, 0.5, 0.5, 0.5),
    "water_dispenser": ("Water dispenser", 90, 24, 24, 24),
    "iron":            ("Iron", 1000, 0.3, 0.3, 0.3),
    "hair_dryer":      ("Hair dryer / straightener", 1200, 0.2, 0.2, 0.2),
    "vacuum":          ("Vacuum cleaner", 1200, 0.2, 0.2, 0.2),
    "led_tv":          ("LED TV", 90, 5, 5, 5),
    "computer":        ("Desktop computer", 200, 5, 5, 5),
    "laptop":          ("Laptop", 60, 6, 6, 6),
    "router":          ("Wi-Fi router", 10, 24, 24, 24),
    "lights":          ("LED lights (each)", 12, 6, 7, 6),
    "air_cooler":      ("Air cooler", 200, 10, 0, 3),
    "air_purifier":    ("Air purifier", 45, 8, 12, 8),
    "ups":             ("UPS charging and losses", 60, 8, 6, 6),
    "room_heater":     ("Room heater", 1500, 0, 3, 0),
    "treadmill":       ("Treadmill", 1500, 0.5, 0.5, 0.5),
}

CUSTOM_WATTS = 100           # an appliance we have no figures for, until the user gives its power


def custom_hours(watts):
    """Hours per day for an appliance we have no figures for (when the user gives none):
    big loads (kettle, air fryer, heater-like) run briefly, small ones (purifier, console) for longer."""
    if watts >= 1000:
        return 0.5
    if watts >= 300:
        return 2
    return 4
SEASON_INDEX = {"summer": 2, "winter": 3, "mild": 4}
AC_TONS = {"ac_noninverter": 1.5, "ac_inverter": 1.5, "ac_1ton_noninverter": 1, "ac_1ton_inverter": 1}


def profile(item):
    """(label, watts, {season: hours}, how) for one appliance line.

    how: "typical" (our figures), "yours" (the user's watts or hours) or "guessed" (unknown appliance, no watts).
    """
    key = item.get("key")
    known = APPLIANCES.get(key)
    watts, hours = item.get("watts"), item.get("hours")
    if known:
        label, typical_w, *season_hours = known
        hrs = dict(zip(SEASON_INDEX, season_hours))
        w = typical_w
        # A 2 ton AC draws about 2 / 1.5 of a 1.5 ton one
        if key in AC_TONS and item.get("ton"):
            w = typical_w * item["ton"] / AC_TONS[key]
            label = label.replace(f"{AC_TONS[key]:g} ton", f"{item['ton']:g} ton")
        if watts:
            w = watts
        # The user's hours replace the busiest season; the other seasons keep the same pattern
        if hours:
            peak = max(hrs.values()) or 1
            hrs = {s: h * hours / peak for s, h in hrs.items()}
        how = "yours" if (watts or hours) else "typical"
    else:
        label = (item.get("label") or "Other appliance").strip().capitalize()
        w = watts or CUSTOM_WATTS
        hrs = dict.fromkeys(SEASON_INDEX, hours or custom_hours(w))
        how = "yours" if watts else "guessed"
    return label, w, hrs, how


def items_from_counts(counts):
    """The old request shape {key: count} as appliance lines."""
    return [{"key": k, "count": n} for k, n in counts.items() if n]


def expected_units(items, season, days=30):
    out = []
    for item in items:
        n = item.get("count") or 1
        label, watts, hrs, how = profile(item)
        units = n * watts * hrs[season] * days / 1000
        out.append({"label": label, "count": n, "watts": round(watts), "how": how, "units": units})
    return out


def breakdown(items, season_avg_units):
    """items: appliance lines [{key, count, label?, watts?, hours?, ton?}].
    season_avg_units: {"summer": avg units per month, "winter": ..., "mild": ...} from the bill."""
    result = {}
    for season, real in season_avg_units.items():
        exp = [e for e in expected_units(items, season) if e["units"] > 0]
        total = sum(e["units"] for e in exp)
        if not total or not real:
            continue
        scale = real / total
        lines = sorted(({"appliance": e["label"], "count": e["count"], "watts": e["watts"], "how": e["how"],
                         "units": round(e["units"] * scale),
                         "share_percent": round(100 * e["units"] / total)} for e in exp),
                       key=lambda x: -x["units"])
        result[season] = {"bill_units": round(real), "typical_units": round(total),
                          "scale": round(scale, 2), "items": lines}
    return result
