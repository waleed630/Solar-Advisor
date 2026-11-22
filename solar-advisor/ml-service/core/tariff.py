"""Monthly electricity bill from units, using slab rates calibrated on real bills."""


def energy_charge(units, status, t):
    """Base charge from the slab table (before adjustments and taxes)."""
    if units <= 0:
        return 0.0
    if status == "tou":
        tou = t["tou"]
        peak = units * tou["peak_share"]
        return (units - peak) * tou["offpeak_rate"] + peak * tou["peak_rate"]
    if status == "protected":
        cost, prev = 0.0, 0
        for s in t["protected_slabs"]:
            top = s["up_to"] or 10**9
            n = max(0, min(units, top) - prev)
            cost += n * s["rate"]
            prev = top
        # Above the protected limit, the remaining units fall into the unprotected table
        if units > prev:
            cost += (units - prev) * t["unprotected_slabs"][-1]["rate"]
        return cost
    # Unprotected: every unit at the rate of the slab the month falls in
    for s in t["unprotected_slabs"]:
        if s["up_to"] is None or units <= s["up_to"]:
            return units * s["rate"]


def monthly_bill(units, status, t):
    """Full bill (charges + adjustments + taxes), calibrated on our own bills."""
    c = t["calibration"]
    base = energy_charge(units, status, t)
    if status == "tou":
        charges = base * c["tou_multiplier"] + c["tou_fixed_per_month"]
    elif status == "protected":
        charges = base + c["protected_extra_per_month"]
    else:
        charges = base * c["unprotected_multiplier"]
    return round(charges * (1 + c["tax_percent"] / 100), 0)


def status_for(month_units, sanctioned_load_kw, t):
    """tou for big loads; protected if no month goes over the protected limit; else unprotected."""
    if sanctioned_load_kw and sanctioned_load_kw >= t["tou"]["applies_from_load_kw"]:
        return "tou"
    if max(month_units) <= t["protected_limit_units"]:
        return "protected"
    return "unprotected"
