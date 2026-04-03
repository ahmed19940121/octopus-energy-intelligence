# 🐙 Octopus Energy Intelligence — Claude Plugin

[![Version](https://img.shields.io/badge/version-0.2.0-blue)](./.claude-plugin/plugin.json)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![API](https://img.shields.io/badge/API-Octopus%20Energy-9c27b0)](https://api.octopus.energy)
[![Requires](https://img.shields.io/badge/requires-Python%203.9%2B-yellow)](https://python.org)

A plugin for **Claude (Anthropic)** that gives Claude live access to Octopus Energy's half-hourly Agile tariff prices, identifies the cheapest time windows for flexible loads (EV charging, washing machine, dishwasher), flags when electricity prices go negative — and optionally analyses your personal smart meter data.

> **No API key required** for live Agile pricing and tariff data. Only personal consumption data needs an Octopus API key.

---

## 🗂️ What's Inside

```
octopus-energy-intelligence/
├── .claude-plugin/
│   └── plugin.json                          # Plugin metadata
├── .mcp.json                                # MCP server configuration
├── servers/
│   └── octopus_server.py                   # Python MCP server (5 tools)
├── skills/
│   ├── octopus-agile-intelligence/SKILL.md
│   └── octopus-smart-optimizer/SKILL.md
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Skills Overview

This plugin provides Claude with **2 specialist skills** that are automatically triggered by natural language:

### 1. `octopus-agile-intelligence`
Gives a daily overview of Agile prices — cheapest slots, spikes, negative prices, and a plain-English verdict on whether today is cheap or expensive.

**Trigger phrases:**
- "Is today a cheap Octopus day?"
- "Agile price summary"
- "What's the Octopus price right now?"
- "Agile rates today"
- "Is electricity cheap today?"
- "Octopus price summary"
- "Are there any negative price slots?"

---

### 2. `octopus-smart-optimizer`
Finds the cheapest consecutive time window for your specific load — EV charging, washing machine, dishwasher, etc. Calculates savings vs the standard rate.

**Trigger phrases:**
- "When should I charge my car?"
- "Best 3-hour window to use energy"
- "Cheapest window tonight"
- "Schedule my EV charge on Octopus"
- "Octopus golden hour"
- "How much will I save on Agile?"
- "When should I run my dishwasher?"

---

## 🔧 MCP Tools Reference

The plugin runs a Python MCP server (`octopus_server.py`) that exposes 5 tools to Claude:

| Tool | Description | Auth required? |
|---|---|---|
| `get_agile_prices` | All 48 half-hourly slots for the next 24 hours | ❌ No |
| `get_golden_windows` | Cheapest consecutive N-hour window for your load | ❌ No |
| `get_agile_price_summary` | Concise daily summary with verdict (cheap/expensive/spike) | ❌ No |
| `get_octopus_tariffs` | Browse all current Octopus tariff products | ❌ No |
| `get_account_consumption` | Personal smart meter data (half-hourly kWh) | ✅ OCTOPUS_API_KEY |

---

## 🕐 How Agile Pricing Works

Octopus Agile is a **half-hourly variable electricity tariff** — prices change every 30 minutes based on wholesale market prices.

- Prices are published **daily at ~4pm** for the following day
- Typically **cheapest overnight** (11pm–7am)
- Typically **most expensive** at evening peak (4pm–7pm)
- Prices can go **negative** — Octopus pays YOU to use electricity
- Prices above **35p/kWh** are spike alerts to avoid heavy loads

**Daily verdict categories used by this plugin:**

| Average p/kWh | Verdict |
|---|---|
| < 5p | 🟢 EXCEPTIONAL — stack all flexible loads |
| 5–12p | 🟢 CHEAP — well below price cap |
| 12–20p | 🟡 REASONABLE — good windows available |
| 20–28p | ⚪ AVERAGE — around standard rate |
| > 28p | 🔴 EXPENSIVE — minimise flexible loads |

---

## 🛠️ Installation

### Prerequisites

- Python 3.9 or later
- `pip`
- Claude desktop app with Cowork or Claude Code (with plugin support)

### Step 1 — Install Python dependencies

```bash
pip install fastmcp requests
```

### Step 2 — Install the plugin in Claude

**Option A — From this repo (Claude Code)**

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/octopus-energy-intelligence.git

# In Claude Code, install it as a local plugin
claude plugin install ./octopus-energy-intelligence
```

**Option B — Manual plugin file**

Drop the entire folder into your Claude plugins directory and restart Claude.

### Step 3 — (Optional) Configure your Octopus API key

Only needed for personal smart meter consumption data.

```bash
# macOS / Linux
export OCTOPUS_API_KEY=sk_live_your_key_here

# Windows PowerShell
$env:OCTOPUS_API_KEY = "sk_live_your_key_here"
```

**How to get your Octopus API key:**
1. Log in at [octopus.energy](https://octopus.energy/dashboard/new/accounts/personal-details)
2. Go to **Personal Details → API access**
3. Copy your API key (starts with `sk_live_`)

> You'll also need your **MPAN** (13-digit meter reference, on your bill) and **meter serial number** (on your bill or in the Octopus app).

---

## 🌍 Region Codes

All tools accept a `region` parameter. Default is **A (Eastern England)**.

| Code | Region |
|---|---|
| A | Eastern England |
| B | East Midlands |
| C | London |
| D | Merseyside & NW |
| E | West Midlands |
| F | North East |
| G | North West |
| H | Southern |
| J | South East |
| K | South Wales |
| L | South Western |
| M | Yorkshire |
| N | North Scotland |
| P | South Scotland |

---

## 💬 Example Conversations

**Daily price check:**
> You: "Is today a cheap Agile day?"
> Claude: Returns average price, min/max, and a plain-English verdict — e.g. "CHEAP DAY 🟡 — avg 14p/kWh, overnight slots dip to 3p."

**EV charging:**
> You: "When's the best time to charge my car tonight?"
> Claude: Finds the cheapest 3-hour window, gives start/end times, avg p/kWh, and how much you save vs the standard rate.

**Appliance scheduling:**
> You: "When should I run my dishwasher?"
> Claude: Identifies the cheapest 1.5-hour window (3 slots) and tells you exact timing in local time (BST or GMT).

**Negative prices:**
> You: "Are there any free electricity slots today?"
> Claude: Flags all negative-price slots — times when Octopus pays you to use electricity.

**Smart meter check:**
> You: "How much have I used this week on Octopus?"
> Claude: Calls `get_account_consumption`, summarises total kWh, daily average, and compares to Agile prices.

---

## 🔌 Data Source

All pricing data is fetched live from:

```
https://api.octopus.energy/v1/
```

No authentication required for tariff and Agile pricing data. Prices are published by Octopus Energy daily at approximately 4pm for the following 24 hours.

---

## 🤝 Contributing

Pull requests welcome! Please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Commit your changes
4. Push and open a Pull Request

**Ideas for contributions:**
- Support for additional Octopus tariffs (Cosy, Flux, Go)
- Multi-day price forecasting
- Home battery charge/discharge optimisation
- Zappi / EV charger integration tips

---

## 📄 License

MIT — see [LICENSE](./LICENSE) for details.

---

## 👤 Author

**nurry** — [ahmednur719@gmail.com](mailto:ahmednur719@gmail.com)

Built as a Cowork plugin for Claude (Anthropic). If you find this useful, ⭐ the repo!
