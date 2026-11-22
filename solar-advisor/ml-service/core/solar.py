"""Solar generation, system size, cost, savings and payback, with and without battery."""
import math

from .tariff import monthly_bill, status_for

DAYS = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
DAYTIME_SHARE = 0.45      # share of a home's units used while the sun is up
BATTERY_EFFICIENCY = 0.9

STRUCTURES = {
    "concrete": {"name": "Elevated GI steel frame", "price_key": "structure_elevated_per_kw",
                 "note": "Face south, tilt about 25 to 30 degrees, 6 to 10 ft high so the roof stays usable."},
    "concrete_low": {"name": "Low-height GI frame", "price_key": "structure_normal_per_kw",
                     "note": "Cheaper, but blocks roof use; keep gaps between rows to avoid shading."},
    "tin": {"name": "Aluminium rails on the sheet or purlins", "price_key": "structure_normal_per_kw",
            "note": "Light weight; check the shed can carry the load."},
    "tiles": {"name": "Rail mount with roof hooks", "price_key": "structure_normal_per_kw",
              "note": "Follows the roof slope."},
    "ground": {"name": "Ground-mount steel structure", "price_key": "structure_elevated_per_kw",
               "note": "For open land; face south, tilt about 30 degrees."},
}


def price(cfg, key):
    return cfg["prices"][key]["value"]


def system_cost(kw, battery_kwh, roof_type, cfg):
    s = STRUCTURES.get(roof_type, STRUCTURES["concrete"])
    inverter_key = "inverter_hybrid_per_kw" if battery_kwh else "inverter_ongrid_per_kw"
    inverter_kw = max(kw, price(cfg, "min_inverter_kw"))   # inverters are not sold smaller than this
    parts = {
        "panels": kw * 1000 * price(cfg, "panel_per_watt"),
        "inverter": inverter_kw * price(cfg, inverter_key),
        "fixed": price(cfg, "fixed_costs"),
        "structure": kw * price(cfg, s["price_key"]),
        "installation": kw * price(cfg, "installation_per_kw"),
        "wiring_protection": kw * price(cfg, "wiring_protection_per_kw"),
        "battery": battery_kwh * price(cfg, "battery_lithium_per_kwh"),
    }
    parts = {k: round(v) for k, v in parts.items()}
    return sum(parts.values()), parts


def simulate(year_units, kw, battery_kwh, sanctioned_load_kw, cfg):
    """Month by month: what solar makes, what the home uses from it, what it buys and sells."""
    t = cfg["tariff_residential"]
    buyback = cfg["net_billing"]["buyback_rate_per_unit"]
    yld = cfg["solar"]["yield_per_kw_month"]
    before_status = status_for(list(year_units.values()), sanctioned_load_kw, t)

    months = []
    for m in range(1, 13):
        use = year_units[m]
        gen = kw * yld[str(m)]
        direct = min(gen, use * DAYTIME_SHARE)
        stored = 0.0
        if battery_kwh:
            stored = min(gen - direct, use - direct, battery_kwh * DAYS[m] * BATTERY_EFFICIENCY)
        imported = use - direct - stored
        exported = gen - direct - stored
        months.append({"month": m, "use": round(use), "solar": round(gen), "self_used": round(direct + stored),
                       "imported": round(imported), "exported": round(exported)})

    after_status = status_for([x["imported"] for x in months], sanctioned_load_kw, t)
    for x in months:
        x["bill_before"] = monthly_bill(x["use"], before_status, t)
        x["bill_after"] = round(monthly_bill(x["imported"], after_status, t) - x["exported"] * buyback)
        x["saving"] = x["bill_before"] - x["bill_after"]
    return months, before_status, after_status


def evaluate_size(year_units, n_panels, battery_kwh, sanctioned_load_kw, roof_type, cfg):
    kw = round(n_panels * price(cfg, "panel_watt") / 1000, 2)
    months, before_status, after_status = simulate(year_units, kw, battery_kwh, sanctioned_load_kw, cfg)
    cost, parts = system_cost(kw, battery_kwh, roof_type, cfg)
    yearly_saving = sum(x["saving"] for x in months)
    payback = round(cost / yearly_saving, 1) if yearly_saving > 0 else None
    life = cfg["solar"]["system_life_years"]
    degr = cfg["solar"]["panel_degradation_percent_per_year"] / 100
    lifetime_saving = sum(yearly_saving * (1 - degr) ** y for y in range(life))
    # Inverters and batteries wear out before the panels: count the replacements in the 25 years
    replacements = (math.ceil(life / cfg["solar"].get("inverter_life_years", life)) - 1) * parts["inverter"]
    if battery_kwh:
        replacements += (math.ceil(life / cfg["solar"].get("battery_life_years", life)) - 1) * parts["battery"]
    return {"panels": n_panels, "kw": kw, "battery_kwh": battery_kwh, "cost": cost, "cost_parts": parts,
            "yearly_saving": round(yearly_saving), "monthly_saving": round(yearly_saving / 12),
            "payback_years": payback, "replacement_cost": round(replacements),
            "lifetime_net_saving": round(lifetime_saving - cost - replacements),
            "solar_per_year": sum(x["solar"] for x in months),
            "covers_percent": round(100 * sum(x["solar"] for x in months) / sum(x["use"] for x in months)),
            "status_before": before_status, "status_after": after_status, "months": months}


def battery_size(year_units):
    """Enough to carry the evening and night share of an average day, in 2.5 kWh steps."""
    daily = sum(year_units.values()) / 365
    return max(2.5, round(daily * (1 - DAYTIME_SHARE) / 2.5) * 2.5)


def plan(year_units, roof_area_sqft, roof_type, sanctioned_load_kw, cfg, max_kw=None):
    """Try every panel count that fits; recommend a size close to the shortest payback but with more savings."""
    panel_w = price(cfg, "panel_watt")
    sqft_per_kw = cfg["solar"]["roof_sqft_per_kw"]
    yearly_units = sum(year_units.values())
    yearly_yield = sum(cfg["solar"]["yield_per_kw_month"].values())

    need_kw = yearly_units / yearly_yield                       # covers the whole year's units
    roof_kw = roof_area_sqft / sqft_per_kw if roof_area_sqft else 1.5 * need_kw
    top_kw = min(roof_kw, 1.5 * need_kw, max_kw or 10**6)
    max_panels = max(1, math.floor(top_kw * 1000 / panel_w))

    def options_for(battery_kwh):
        opts = [evaluate_size(year_units, n, battery_kwh, sanctioned_load_kw, roof_type, cfg)
                for n in range(1, max_panels + 1)]
        valid = [o for o in opts if o["payback_years"]]
        if not valid:
            return opts, None
        best_pb = min(o["payback_years"] for o in valid)
        close = [o for o in valid if o["payback_years"] <= best_pb * 1.15]
        return opts, max(close, key=lambda o: o["lifetime_net_saving"])

    no_batt_opts, no_batt = options_for(0)
    batt_kwh = battery_size(year_units)
    _, with_batt = options_for(batt_kwh)

    s = STRUCTURES.get(roof_type, STRUCTURES["concrete"])
    rec = no_batt or no_batt_opts[-1]
    return {
        "yearly_units": round(yearly_units),
        "kw_to_cover_full_year": round(need_kw, 1),
        "roof": {"area_sqft": roof_area_sqft, "max_kw_on_roof": round(roof_kw, 1) if roof_area_sqft else None,
                 "needed_sqft": round(rec["kw"] * sqft_per_kw), "fits": (not roof_area_sqft) or rec["kw"] <= roof_kw},
        "structure": {"type": roof_type, "name": s["name"], "note": s["note"]},
        "recommended": rec,
        "with_battery": with_batt,
        "size_options": [{k: o[k] for k in ("panels", "kw", "cost", "yearly_saving", "payback_years", "covers_percent")}
                         for o in no_batt_opts],
    }
