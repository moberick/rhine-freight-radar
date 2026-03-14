"""
app.py – Rhine Freight Radar Dashboard
=======================================
Streamlit front-end that displays live water levels at the Kaub gauge,
short-term forecasts, and an interactive Kleinwasserzuschlag calculator.
"""

import csv
import os
import streamlit as st
from datetime import datetime

from data_fetcher import get_current_level, get_forecast, get_historical_data, STATIONS
from calculator import calculate_surcharge, compare_freight_costs
import pandas as pd

SUBSCRIBERS_FILE = "subscribers.csv"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Rhine Freight Radar",
    page_icon="🚢",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Fetch live data
# ---------------------------------------------------------------------------
st.title("🚢 Rhine Freight Radar")
st.caption("Live water-level intelligence for Rhine logistics")

selected_station = st.selectbox(
    "Select River Station",
    options=list(STATIONS.keys()),
    index=0,
)

current = get_current_level(selected_station)
forecast = get_forecast(selected_station)

if "error" in current:
    st.error(f"Could not fetch current water level: {current['error']}")
    current_cm = 150  # sensible fallback for the slider default
else:
    current_cm = int(current["value"])
    ts = datetime.fromisoformat(current["timestamp"])

    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric(
            label=f"Water Level at {selected_station}",
            value=f"{current_cm} cm",
            help="Live reading from the PEGELONLINE API",
        )
    with col2:
        status = current.get("state_mnw_mhw", "—")
        st.metric(label="Status", value=status.capitalize())

    st.caption(f"Last measured: **{ts.strftime('%d %b %Y, %H:%M')}** (CET)")

st.divider()

# ---------------------------------------------------------------------------
# Forecast summary
# ---------------------------------------------------------------------------
st.subheader("📈 3-Day Forecast")

if "error" in forecast:
    st.warning(f"Forecast unavailable: {forecast['error']}")
else:
    forecasts = forecast.get("forecasts", [])
    if forecasts:
        max_entry = max(forecasts, key=lambda e: e["value"])
        min_entry = min(forecasts, key=lambda e: e["value"])

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            st.metric("Peak forecast", f"{max_entry['value']:.0f} cm")
        with fc2:
            st.metric("Low forecast", f"{min_entry['value']:.0f} cm")
        with fc3:
            st.metric("Data points", forecast["count"])

        ts_init = datetime.fromisoformat(forecast["initialized"])
        st.caption(
            f"Forecast issued: **{ts_init.strftime('%d %b %Y, %H:%M')}** "
            f"· Source: BfG (Bundesanstalt für Gewässerkunde)"
        )
    else:
        st.info("No future forecast data points available right now.")

st.divider()

# ---------------------------------------------------------------------------
# 30-Day Historical Trend
# ---------------------------------------------------------------------------
st.subheader("📉 30-Day Water Level Trend")

history_df = get_historical_data(selected_station, days=30)

if history_df.empty:
    st.info(f"No historical data available for {selected_station}.")
else:
    chart_df = history_df.set_index("timestamp")[["value"]]
    chart_df = chart_df.rename(columns={"value": "Water Level (cm)"})
    st.line_chart(chart_df, color="#4DA6FF")

st.divider()

# ---------------------------------------------------------------------------
# Interactive surcharge calculator
# ---------------------------------------------------------------------------
st.subheader("💰 Kleinwasserzuschlag Calculator")
st.markdown(
    "Simulate how changes in the Kaub water level affect your freight costs."
)

calc_col1, calc_col2 = st.columns(2)

with calc_col1:
    cargo_tons = st.number_input(
        "Cargo Volume (Tons)",
        min_value=1,
        max_value=100_000,
        value=1000,
        step=100,
    )

with calc_col2:
    sim_level = st.slider(
        "Simulate Water Level (cm)",
        min_value=50,
        max_value=250,
        value=current_cm,
    )

# Calculate
result = calculate_surcharge(water_level_cm=sim_level, cargo_tonnage=cargo_tons)

per_ton = result["surcharge_per_ton"]
total = result["total_surcharge"]

st.markdown("---")

# Display result with conditional severity
if sim_level < 80:
    st.error(
        f"🚨 **Critical low water!**  Surcharge: **€{per_ton:.2f}/ton**  ·  "
        f"Total: **€{total:,.2f}** on {cargo_tons:,} tons"
    )
elif total > 0:
    st.warning(
        f"⚠️ **Low-water surcharge active.**  Surcharge: **€{per_ton:.2f}/ton**  ·  "
        f"Total: **€{total:,.2f}** on {cargo_tons:,} tons"
    )
else:
    st.success(
        f"✅ **No surcharge.**  Water level ({sim_level} cm) is above the "
        f"150 cm threshold.  Shipping at standard rates."
    )

# ---------------------------------------------------------------------------
# Freight Cost Comparator
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🚛 Freight Alternative Costs")

costs = compare_freight_costs(cargo_tons, total)

df_costs = pd.DataFrame(
    {"Mode": list(costs.keys()), "Total Cost (€)": list(costs.values())}
).set_index("Mode")

st.bar_chart(df_costs, color="#4DA6FF")

# Dynamic recommendation
cheapest_mode = min(costs, key=costs.get)
cheapest_cost = costs[cheapest_mode]
barge_cost = costs["Barge"]

if cheapest_mode == "Barge":
    st.success(
        f"✅ **Barge is the cheapest option** at €{barge_cost:,.2f} for "
        f"{cargo_tons:,} tons."
    )
else:
    saving = barge_cost - cheapest_cost
    st.info(
        f"💡 **{cheapest_mode} is currently €{saving:,.2f} cheaper** than "
        f"Barge transport (€{cheapest_cost:,.2f} vs €{barge_cost:,.2f})."
    )

# Surcharge tier reference table
with st.expander("📋 Surcharge tier reference"):
    st.markdown(
        """
        | Kaub Level (cm) | Surcharge (€/ton) |
        |:---------------:|:-----------------:|
        | > 150           | €0                |
        | 131 – 150       | €15               |
        | 111 – 130       | €30               |
        | 91 – 110        | €45               |
        | 80 – 90         | €65               |
        | < 80            | €90               |
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Email subscription form
# ---------------------------------------------------------------------------
with st.expander("🔔 Setup Automated Email Alerts"):
    st.markdown(
        "**How it works:** Enter your email and your critical water level "
        "threshold. Our system monitors the Kaub gauge 24/7. We will only "
        "send you an alert if the water drops below your threshold, warning "
        "you of incoming surcharges."
    )

    with st.form("subscribe_form"):
        email_input = st.text_input("Email Address")
        threshold_input = st.number_input(
            "Alert Threshold (cm)",
            min_value=50,
            max_value=250,
            value=130,
            step=5,
        )
        submitted = st.form_submit_button("Subscribe to Alerts")

    if submitted:
        if not email_input or "@" not in email_input:
            st.error("Please enter a valid email address.")
        else:
            file_exists = os.path.isfile(SUBSCRIBERS_FILE)
            with open(SUBSCRIBERS_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["email", "threshold_cm"])
                writer.writerow([email_input, threshold_input])
            st.success("You are set up! We will monitor the river for you.")
