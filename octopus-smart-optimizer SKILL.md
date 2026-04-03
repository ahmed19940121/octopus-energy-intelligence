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
- Wa