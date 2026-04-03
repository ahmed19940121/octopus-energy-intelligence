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
- avg 5–12p → **CHEAP** — well below cap, excellent shift day
- avg 12–20p → **AVERAGE** — below cap, smart scheduling still saves
- avg 20–28p → **EXPENSIVE** — at or above cap, shift only priority loads
- avg > 28p → **SPIKE** — higher than cap, avoid all heavy loads
 
**2. Key numbers** — average p/kWh, minimum slot (price + local time),
maximum slot (price + local time), percentage vs 24.5p Ofgem cap.
 
**3. Negative slot alert** — if any value_inc_vat < 0, list each slot's exact
local time and price. Flag clearly: Octopus is paying you to use electricity.
 
**4. Near-zero alert** — if no negatives, list any slots below 2p/kWh.
 
**5. Cheapest 2-hour window** — find the 4 consecutive slots with the lowest sum.
Report: start time (local), end time (local), average p/kWh.
 
**6. Cheapest 4-hour window** — find the 8 consecutive slots with the lowest sum.
Report: start time (local), end time (local), average p/kWh.
 
**7. Actionable tip** — one sentence on when to run the heaviest loads.
 
## Data freshness
 
Octopus publishes next-day prices at approximately 4pm UK time. If fewer than
48 slots are returned, note how many are available and present what was returned.
Never fabricate or estimate prices — only use what the API returns.
