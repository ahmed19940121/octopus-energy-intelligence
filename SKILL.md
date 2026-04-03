---
name: octopus-agile-intelligence
description: >
  Use this skill when the user asks about Octopus Energy Agile tariff prices,
  half-hourly electricity rates, when electricity is cheapest today, Agile price
  spikes, negative electricity prices (getting paid to use electricity), today's
  Agile overview, or whether it's a cheap or expensive energy day.
  Also trigger for: "what's the Octopus price right now", "Agile rates today",
  "when should I run my dishwasher", "cheapest electricity slot", "Octopus price
  summary", "is electricity cheap today".
metadata:
  version: "0.2.0"
---

## IMPORTANT: Do not call any MCP tools or use ToolSearch.
## Go directly to WebFetch on the Octopus public REST API — no authentication required.

## Step 1 — Fetch live prices via WebFetch

Call WebFetch on this URL. Replace TODAY and TOMORROW with actual dates in
YYYY-MM-DD format (TODAY = current date, TOMORROW = current date + 1 day):

```
https://api.octopus.energy/v1/products/AGILE-24-10-01/electricity-tariffs/E-1R-AGILE-24-10-01-A/standard-unit-rates/?page_size=48&period_from=TODAYt00:00:00Z&period_to=TOMORROWt00:00:00Z
```

Use this exact WebFetch prompt to prevent numeric misinterpretation:
> "Return each result object's exact raw value_inc_vat number exactly as it appears
> in the JSON — do not convert, multiply, divide, or round. Include valid_from and
> valid_to for every entry. All timestamps are UTC. Do not convert to local time.
> List all results sorted by valid_from ascending."

**Region:** Default is A (Eastern England). Replace the final letter in the tariff
code to change region: E-1R-AGILE-24-10-01-**A**
Codes: A=Eastern, B=East Midlands, C=London, D=Merseyside/NW, E=West Midlands,
F=North East, G=North West, H=Southern, J=South East, K=South Wales,
L=South Western, M=Yorkshire, N=North Scotland, P=South Scotland.

## Step 2 — Timezone conversion rule

All API timestamps are UTC (Z suffix). Convert to local UK time before presenting:
- **BST (UTC+1):** last Sunday of March → last Sunday of October
- **GMT (UTC+0):** all other months
Label every time in your response with BST or GMT as appropriate.

## Step 3 — Compute and present

value_inc_vat is already in pence per kWh including VAT. Do not adjust it.

**1. Daily verdict** — compute average across all returned slots, then classify:
- avg < 5p → **EXCEPTIONAL** — near-zero grid prices, stack all loads
- avg 5–12p → **CHEAP** — well below cap, ex