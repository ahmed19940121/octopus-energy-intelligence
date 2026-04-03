"""
Octopus Energy Intelligence MCP Server
=======================================
Connects Claude to Octopus Energy's public REST API.
No API key required for tariff/pricing data.
Optional: Set OCTOPUS_API_KEY for personal account consumption data.

Install:
  pip install fastmcp requests

Data sources:
  - Octopus Energy API v1 (api.octopus.energy)
"""
import os
import requests
from datetime import datetime, timezone, timedelta
from fastmcp import FastMCP

mcp = FastMCP("Octopus Energy Intelligence")

BASE = "https://api.octopus.energy/v1"
TIMEOUT = 10
OCTOPUS_API_KEY = os.environ.get("OCTOPUS_API_KEY", "")

# ── Typical standard-rate unit cost (pence/kWh) for comparison baseline
STANDARD_RATE_PPK = 24.5  # approx Ofgem Q1 2025 cap


def _get(url: str, params: dict = None, auth: tuple = None) -> dict | list | None:
    try:
        r = requests.get(url, params=params, auth=auth, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _find_agile_product() -> tuple[str, str]:
    """
    Dynamically locate the current live Octopus Agile electricity product.
    Returns (product_code, tariff_code) for region A (Eastern England as default).
    Octopus product codes change when new versions launch — always discover dynamically.
    """
    data = _get(f"{BASE}/products/", params={"is_variable": "true", "brand": "OCTOPUS_ENERGY"})
    if isinstance(data, dict) and "error" in data:
        return None, None
    products = data.get("results", []) if isinstance(data, dict) else []
    for p in products:
        code = p.get("code", "")
        if "AGILE" in code.upper() and p.get("is_prepay") is False:
            # Build tariff code for single-rate (E-1R) electricity in region A
            tariff_code = f"E-1R-{code}-A"
            return code, tariff_code
    return None, None


# ═══════════════════════════════════════════════════════════════════════
# TOOL 1 — Live Agile half-hourly prices (next 24 hours)
# ═══════════════════════════════════════════════════════════════════════
@mcp.tool
def get_agile_prices(region: str = "A") -> dict:
    """
    Get Octopus Agile electricity tariff half-hourly unit rates for the next 24 hours.
    Returns all upcoming slots in pence per kWh (p/kWh), sorted chronologically.
    Agile prices vary every 30 minutes based on wholesale market prices —
    typically cheapest overnight (11pm–7am) and most expensive at evening peak (4–7pm).
    Region codes: A=Eastern, B=East Midlands, C=London, D=Merseyside, E=West Midlands,
                  F=North East, G=North West, H=Southern, J=South East, K=South Wales,
                  L=South Western, M=Yorkshire, N=North Scotland, P=South Scotland.
    """
    product_code, _ = _find_agile_product()
    if not product_code:
        return {"error": "Could not locate current Agile product. Octopus may have updated their product range."}

    tariff_code = f"E-1R-{product_code}-{region.upper()}"
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(hours=24)

    data = _get(
        f"{BASE}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
        params={
            "period_from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "period_to": tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "page_size": 48,
        }
    )
    if isinstance(data, dict) and "error" in data:
        return {"error": data["error"]}

    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        return {"error": "No Agile price data returned — prices may not yet be published for this period."}

    slots = []
    for r in results:
        slots.append({
            "period_from": r.get("valid_from"),
            "period_to":   r.get("valid_to"),
            "price_pence_per_kwh": round(r.get("value_inc_vat", 0), 4),
        })
    slots.sort(key=lambda x: x["period_from"] or "")

    prices = [s["price_pence_per_kwh"] for s in slots]
    avg = round(sum(prices) / len(prices), 2) if prices else None
    negative_slots = [s for s in slots if s["price_pence_per_kwh"] < 0]

    return {
        "product_code":    product_code,
        "tariff_code":     tariff_code,
        "region":          region.upper(),
        "slot_count":      len(slots),
        "avg_price_ppk":   avg,
        "min_price_ppk":   min(prices) if prices else None,
        "max_price_ppk":   max(prices) if prices else None,
        "negative_slots":  len(negative_slots),
        "negative_alert":  len(negative_slots) > 0,
        "slots":           slots,
        "note": "Prices in pence/kWh inclusive of VAT. Published by Octopus Energy daily at ~4pm.",
    }


# ═══════════════════════════════════════════════════════════════════════
# TOOL 2 — Golden Windows: best time slots to use energy
# ═══════════════════════════════════════════════════════════════════════
@mcp.tool
def get_golden_windows(region: str = "A", window_hours: float = 3.0) -> dict:
    """
    Calculate the cheapest consecutive time windows in the next 24 hours on the Agile tariff.
    Identifies: the single cheapest N-hour window (ideal for EV charging, dishwasher, washing machine),
    all negative-price slots (when Octopus pays YOU to use electricity),
    and a recommendation for smart appliance scheduling.
    window_hours: length of the window in hours (default 3, e.g. 1, 2, 3, 4).
    """
    price_data = get_agile_prices(region=region)
    if "error" in price_data:
        return price_data

    slots = price_data.get("slots", [])
    if not slots:
        return {"error": "No price slots available to compute windows."}

    n_slots = int(window_hours * 2)  # 2 slots per hour (30-min intervals)
    if n_slots > len(slots):
        n_slots = len(slots)

    # Sliding window to find cheapest consecutive n_slots
    best_start = 0
    best_cost = float("inf")
    for i in range(len(slots) - n_slots + 1):
        window_cost = sum(s["price_pence_per_kwh"] for s in slots[i : i + n_slots])
        if window_cost < best_cost:
            best_cost = window_cost
            best_start = i

    best_window = slots[best_start : best_start + n_slots]
    window_avg = round(best_cost / n_slots, 2)
    negative_slots = [s for s in slots if s["price_pence_per_kwh"] < 0]

    # Savings estimate vs standard rate (assume 10 kWh load over the window)
    kwh_per_window = window_hours * 3.3  # approx EV at 3.3 kW
    standard_cost_p = round(kwh_per_window * STANDARD_RATE_PPK, 1)
    agile_cost_p    = round(kwh_per_window * window_avg, 1)
    saving_p        = round(standard_cost_p - agile_cost_p, 1)

    return {
        "region":           region.upper(),
        "window_hours":     window_hours,
        "cheapest_window": {
            "start":        best_window[0]["period_from"],
            "end":          best_window[-1]["period_to"],
            "avg_price_ppk": window_avg,
            "all_slots":    best_window,
        },
        "negative_price_slots": negative_slots,
        "ev_charge_example": {
            "assumed_load_kw":    3.3,
            "kwh_in_window":      round(kwh_per_window, 1),
            "cost_at_agile_p":    agile_cost_p,
            "cost_at_standard_p": standard_cost_p,
            "estimated_saving_p": saving_p,
        },
        "recommendation": (
            f"Best {window_hours}h window starts at {best_window[0]['period_from']} "
            f"at avg {window_avg}p/kWh — saving ~{saving_p}p vs standard rate on a {round(kwh_per_window,1)} kWh load."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════
# TOOL 3 — List current Octopus electricity tariff products
# ═══════════════════════════════════════════════════════════════════════
@mcp.tool
def get_octopus_tariffs() -> dict:
    """
    List all current Octopus Energy electricity tariff products including
    Agile, Go, Tracker, Cosy, Flux, and fixed-rate options.
    Returns product name, code, whether it's variable, and a brief description.
    Useful for comparing which tariff suits different usage patterns.
    """
    data = _get(f"{BASE}/products/",
                params={"is_prepay": "false", "brand": "OCTOPUS_ENERGY", "page_size": 50})
    if isinstance(data, dict) and "error" in data:
        return data

    results = data.get("results", []) if isinstance(data, dict) else []
    tariffs = []
    for p in results:
        if p.get("direction") != "IMPORT":
            continue
        tariffs.append({
            "code":        p.get("code"),
            "name":        p.get("full_name") or p.get("display_name"),
            "is_variable": p.get("is_variable"),
            "is_green":    p.get("is_green"),
            "description": p.get("description", "")[:200],
            "available_from": p.get("available_from"),
            "available_to":   p.get("available_to"),
        })
    return {
        "total_products": len(tariffs),
        "tariffs": tariffs,
        "note": "Import tariffs only (OCTOPUS_ENERGY brand). Prices vary by region — use get_agile_prices for live Agile rates.",
    }


# ═══════════════════════════════════════════════════════════════════════
# TOOL 4 — Octopus Agile price forecast summary (min/avg/max + spike alert)
# ═══════════════════════════════════════════════════════════════════════
@mcp.tool
def get_agile_price_summary(region: str = "A") -> dict:
    """
    Get a concise daily Agile price summary: min, max, average price today,
    spike alert (price > 35p/kWh), negative-price alert, and a plain-English
    interpretation of whether today is a cheap or expensive Agile day.
    Quick alternative to get_agile_prices when you don't need every half-hourly slot.
    """
    price_data = get_agile_prices(region=region)
    if "error" in price_data:
        return price_data

    slots = price_data.get("slots", [])
    prices = [s["price_pence_per_kwh"] for s in slots]
    if not prices:
        return {"error": "No price data available."}

    avg = price_data["avg_price_ppk"]
    min_p = price_data["min_price_ppk"]
    max_p = price_data["max_price_ppk"]
    neg   = price_data["negative_slots"]
    spike_slots = [s for s in slots if s["price_pence_per_kwh"] > 35]

    verdict = (
        "VERY CHEAP DAY 🟢 — Agile prices well below standard rate. Ideal for shifting loads."
        if avg < 10 else
        "CHEAP DAY 🟡 — Agile prices below standard rate. Good day for flexible loads."
        if avg < 20 else
        "AVERAGE DAY ⚪ — Agile prices around standard rate. Select windows carefully."
        if avg < 28 else
        "EXPENSIVE DAY 🔴 — Agile prices above standard rate. Minimise flexible loads today."
    )

    return {
        "region":           region.upper(),
        "slot_count":       len(slots),
        "avg_price_ppk":    avg,
        "min_price_ppk":    min_p,
        "max_price_ppk":    max_p,
        "negative_slots":   neg,
        "negative_alert":   neg > 0,
        "spike_slots":      len(spike_slots),
        "spike_alert":      len(spike_slots) > 0,
        "daily_verdict":    verdict,
        "standard_rate_ppk": STANDARD_RATE_PPK,
        "vs_standard":      round(avg - STANDARD_RATE_PPK, 2),
    }


# ═══════════════════════════════════════════════════════════════════════
# TOOL 5 — Optional: smart meter consumption (requires API key)
# ═══════════════════════════════════════════════════════════════════════
@mcp.tool
def get_account_consumption(mpan: str, serial_number: str, days_back: int = 7) -> dict:
    """
    Fetch your personal electricity consumption from an Octopus smart meter.
    Requires OCTOPUS_API_KEY environment variable to be set.
    mpan: your electricity meter point reference number (13 digits).
    serial_number: your meter serial number (on your bill or MyOctopus account).
    days_back: how many days of history to retrieve (default 7, max 30).
    Returns half-hourly consumption in kWh for each period.
    """
    if not OCTOPUS_API_KEY:
        return {
            "error": "OCTOPUS_API_KEY not configured",
            "action": (
                "1. Log in to MyOctopus at https://octopus.energy/dashboard/new/accounts/personal-details "
                "2. Go to Personal Details → API access → copy your API key. "
                "3. Set the OCTOPUS_API_KEY environment variable before starting this server. "
                "4. Your MPAN and serial number are on your bill or in the MyOctopus app."
            ),
        }
    from_dt = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    data = _get(
        f"{BASE}/electricity-meter-points/{mpan}/meters/{serial_number}/consumption/",
        params={"period_from": from_dt, "page_size": days_back * 48, "order_by": "period"},
        auth=(OCTOPUS_API_KEY, ""),
    )
    if isinstance(data, dict) and "error" in data:
        return data

    results = data.get("results", []) if isinstance(data, dict) else []
    total_kwh = round(sum(r.get("consumption", 0) for r in results), 3)
    daily_avg = round(total_kwh / days_back, 3) if days_back else 0

    return {
        "mpan":            mpan,
        "serial_number":   serial_number,
        "period_days":     days_back,
        "total_kwh":       total_kwh,
        "daily_avg_kwh":   daily_avg,
        "half_hourly_readings": results,
        "note": "Consumption data is half-hourly in kWh. Smart meter reads may lag by up to 24 hours.",
    }


if __name__ == "__main__":
    mcp.run()
