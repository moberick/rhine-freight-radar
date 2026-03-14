# 🚢 Rhine Freight Radar

**Live App:** [Insert your Streamlit Cloud URL here]

The Rhine River is the central artery for European industrial logistics. When water levels drop at critical chokepoints (like Kaub), barges must "light load," triggering a legally binding Low Water Surcharge (*Kleinwasserzuschlag*). This can cost supply chain managers tens of thousands of Euros overnight. 

The **Rhine Freight Radar** is a lightweight SaaS prototype that tracks real-time hydrology data, calculates financial risk, and alerts logistics teams *before* surcharges destroy their freight margins.

## ✨ Key Features
* **Live Hydrology Tracking:** Pulls real-time water depth and 3-day forecasts for major chokepoints (Kaub, Ruhrort, Maxau) using the German Federal Waterways API (`PEGELONLINE`).
* **Dynamic Surcharge Calculator:** Translates water depth into actual financial risk (€ per ton) based on standard European inland shipping surcharge brackets.
* **"Plan B" Freight Comparator:** Automatically calculates when the barge surcharge becomes so expensive that switching to Rail or Trucking becomes the cheaper alternative.
* **Historical Drought Context:** Visualizes the 30-day water level trend to help procurement teams spot impending droughts.
* **Automated Alert Engine:** A decoupled backend script that monitors the river 24/7 and emails users when the water drops below their custom risk threshold.

## 🛠️ The Tech Stack
Built entirely in Python for maximum speed and data processing capability.
* **Front-End:** `Streamlit`, `Pandas`
* **Back-End/Data:** `Requests`, `PEGELONLINE API`
* **Alert Engine:** `smtplib`, `PythonAnywhere` (Cron jobs)

## 📂 Architecture
* `app.py`: The Streamlit dashboard and user interface.
* `data_fetcher.py`: Handles API connections and data parsing.
* `calculator.py`: The core business logic and math engine.
* `notifier.py`: The headless alert engine designed to run via daily cron jobs.
* `requirements.txt`: Project dependencies.

## 🚀 Local Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YourUsername/rhine-freight-radar.git](https://github.com/YourUsername/rhine-freight-radar.git)
   cd rhine-freight-radar
