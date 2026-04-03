---
name: octopus-smart-optimizer
description: >
  Use this skill when the user wants to optimise their energy use on Octopus Agile,
  find the best time to charge their EV, schedule their dishwasher or washing machine,
  find cheapest consecutive hours on Octopus, calculate energy cost savings, identify
  golden windows, or shift flexible loads to off-peak Agile slots.
  Also trigger for: "when should I charge my car", "best 3 hours to use energy",
  "cheapest window tonight", "schedule my EV charge", "Octopus golden hour",
  "how much will I save", "negative price alert Octopus".
metadata:
  version: "0.2.0"
---
 
## IMPORTANT: Do not call any MCP tools or use ToolSearch.
## Go directly to WebFetch on the Octopus public REST API — no authentication required.
 
## Step 1 — Fetch all half-hourly slots via WebFetch
 
Call WebFetch on this URL. Replace TODAY and TOMORROW with actual dates YYYY-MM-DD:
 
```
https://api.octopus.energy/v1/products/AGILE-24-10-01/electricity-tariffs/E-1R-AGILE-24-10-01-A/standard-unit-rates/?page_size=48&period_from=TODAYt00:00:00Z&period_to=TOMORROWt00:00:00Z
```
 
Use this exact WebFetch prompt:
> "Return each result object's exact raw value_inc_vat number exactly as it appears
> in the JSON — do not convert, multiply, divide, or round. Include valid_from and
> valid_to for every entry. All timestamps are UTC. Do not convert to local time.
> List all results sorted by valid_from ascending."
 
**Region:** Default A (Eastern England). Replace final letter in tariff code for
other regions: A=Eastern, B=East Midlands, C=London, D=Merseyside/NW,
E=West Midlands, F=North East, G=North West, H=Southern, J=South East,
K=South Wales, L=South Western, M=Yorkshire, N=North Scotland, P=South Scotland.
 
## Step 2 — Timezone rule
 
All UTC timestamps → add 1 hour for BST (late Mar–late Oct) or keep as GMT.
Label all times in responses with BST or GMT.
 
## Step 3 — Find golden windows
 
value_inc_vat is already in p/kWh inc. VAT. Do not adjust it.
 
To find the cheapest N-hour window (= 2N consecutive 30-min slots):
1. Compute the sum of each group of 2N consecutive slots
2. The group with the lowest sum is the golden window
3. Report its start time (local), end time (local), and average p/kWh
 
**Default window sizes by appliance** (use these unless the user specifies):
- Washing machine: 2-hour window (4 slots), ~2 kWh
- Dishwasher: 1.5-hour window (3 slots), ~1.5 kWh
- EV charge at 7kW: 3-hour window (6 slots), ~21 kWh
- EV charge at 3.6kW: 4-hour window (8 slots), ~14 kWh
- Immersion heater: 2-hour window (4 slots), ~4 kWh
- Heat pump: 4-hour window (8 slots), varies
 
## Step 4 — Present the recommendation
 
1. **Golden window** — "Your cheapest [N]-hour window today is [START] to [END]
   (local time) at an average of [X]p/kWh."
 
2. **Cost estimate** — Calculate: kWh × avg_rate / 100 = cost in pence and £.
   Compare to standard cap (24.5p/kWh): show saving in pence and £.
 
3. **Negative price slots** — if any value_inc_vat < 0, highlight prominently.
   These are exceptional: Octopus is paying you to consume electricity.
   List each slot's local time and price. Recommend running everything possible.
 
4. **Non-overlapping schedule** — if the user mentions multiple appliances,
   assign each to its own cheapest non-overlapping window. Start with the
   highest-kWh load first (it benefits most from the cheapest slot).
 
## Cost calculation baseline
 
Compare against the Ofgem price cap standard rate (~24.5p/kWh) unless the user
specifies their actual tariff rate, in which case use that for the comparison.
 
