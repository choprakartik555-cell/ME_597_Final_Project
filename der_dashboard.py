"""
Battery Health Monitor — Streamlit App
Run with: streamlit run battery_monitor.py
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
import random

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Battery Health Monitor", page_icon="🔋", layout="wide")

EPS = 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# FUN FACTS
# ─────────────────────────────────────────────────────────────────────────────
BATTERY_FACTS = [
    "🔋 Lithium-ion batteries power everything from phones to electric cars.",
    "⚡ Fast charging can degrade battery life faster due to heat.",
    "🌡️ High temperatures are one of the biggest enemies of battery health.",
    "🔁 Most batteries are considered 'end-of-life' at 80% capacity.",
    "🚗 EV batteries can last 8–15 years depending on usage and climate.",
    "📱 Keeping your battery between 20–80% increases lifespan.",
    "🔬 Battery degradation happens even when not in use (calendar aging).",
]

# Random fact
fact = random.choice(BATTERY_FACTS)


# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────
DEVICES = {
    "Smartwatch 🕐": {
        "capacity_Wh": 1.5,
        "charge_power_W": 2.0,
        "charge_threshold": 0.20,
        "charge_target": 0.95,
        "states": ["Idle", "Active", "Workout"],
        "power_W": [0.02, 0.10, 0.30],
        "transition": [[0.8,0.18,0.02],[0.3,0.6,0.1],[0.2,0.5,0.3]],
        "color": "#00C2B5",
    },
    "Smartphone 📱": {
        "capacity_Wh": 15.0,
        "charge_power_W": 12.0,
        "charge_threshold": 0.20,
        "charge_target": 0.90,
        "states": ["Idle","Light Use","Heavy Use"],
        "power_W": [0.2,1.0,3.5],
        "transition": [[0.7,0.25,0.05],[0.4,0.5,0.1],[0.2,0.3,0.5]],
        "color": "#F5A623",
    },
    "Electric Vehicle 🚗": {
        "capacity_Wh": 80000,
        "charge_power_W": 7000,
        "charge_threshold": 0.20,
        "charge_target": 0.85,
        "states": ["Parked","City","Highway"],
        "power_W": [30,15000,45000],
        "transition": [[0.975,0.015,0.01],[0.6,0.38,0.02],[0.3,0.1,0.6]],
        "color": "#7B8FF5",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
def get_temp_K(hour, mean_C, amp):
    return mean_C + amp * np.sin(2*np.pi*(hour-4380)/8760) + 273.15


def generate_load(device, n, seed):
    rng = np.random.default_rng(seed)
    state = 0
    load = np.zeros(n)
    for i in range(n):
        load[i] = device["power_W"][state]
        state = rng.choice(len(device["power_W"]), p=device["transition"][state])
    return load


@st.cache_data
def run_sim(device, mean_C, amp, n, seed):
    cap_nom = device["capacity_Wh"]
    x = cap_nom * 0.8
    cap_fade = 0

    load = generate_load(device, n, seed)

    soc, cap, temp, state_arr = [], [], [], []

    charging = False

    for k in range(n):
        T = get_temp_K(k, mean_C, amp)
        temp.append(T-273.15)

        cap_eff = max(cap_nom*(1-cap_fade), EPS)

        cur_soc = x/cap_eff

        if cur_soc <= device["charge_threshold"]:
            charging = True
        if cur_soc >= device["charge_target"]:
            charging = False

        net = device["charge_power_W"] if charging else -load[k]

        x += net

        # degradation
        k_cycle = 8e-6
        k_cal = 3e-7
        Ea = 4500

        arr = np.exp(np.clip(Ea*(1/298 - 1/T), -5, 5))
        cap_fade += k_cycle*abs(net)/cap_nom + k_cal*arr
        cap_fade = min(cap_fade, 0.4)

        cap_eff = max(cap_nom*(1-cap_fade), EPS)
        x = np.clip(x, 0, cap_eff)

        soc.append(x/cap_eff)
        cap.append(1-cap_fade)
        state_arr.append(1 if charging else 0)

    soc = np.array(soc)
    cap = np.array(cap)

    idx = np.where(cap <= 0.8)[0]
    life = idx[0] if len(idx)>0 else n

    return {
        "soc": soc,
        "cap": cap,
        "temp": np.array(temp),
        "state": np.array(state_arr),
        "load": load,
        "life": life
    }


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
st.title("🔋 Meet BATTHEALTH - Your Battery Health Assistant")

# ── HERO SECTION (GIF + FACTS) ───────────────────────────────────────────────
col1, col2 = st.columns([1,1])

with col1:
    st.markdown("### ⚡ Battery in Action")
    st.image(
        "https://media.giphy.com/media/l0HlQ7LRalQqdWfao/giphy.gif",
        caption="Charging & discharging cycles (conceptual)",
        use_container_width=True,
    )

with col2:
    st.markdown("### 💡 Did You Know?")
    st.info(fact)

    st.markdown("""
    #### 🔍 What this app does
    - Simulates real battery usage patterns  
    - Models charging & discharging cycles  
    - Estimates battery aging over time  
    - Predicts when battery reaches 80% health  
    """)

st.markdown("---")

# ── CONTROLS ────────────────────────────────────────────────────────────────
device_name = st.selectbox("Device", list(DEVICES.keys()))
device = DEVICES[device_name]

mean_C = st.slider("Mean Temp in your city (°C)", -10, 40, 20)
amp = st.slider("Seasonal Variation", 0, 25, 10)

years = st.slider("Years", 1, 5, 1)
n = years*8760

# ── RUN ─────────────────────────────────────────────────────────────────────
if st.button("Run Simulation"):
    res = run_sim(device, mean_C, amp, n, 42)

    st.subheader("📊 Key Metrics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Final SoC", f"{res['soc'][-1]*100:.1f}%")
    col2.metric("Final Capacity", f"{res['cap'][-1]*100:.1f}%")
    col3.metric("Life (hrs)", res["life"])

    # SoC
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=res["soc"], mode="lines"))
    fig.update_layout(title="State of Charge")
    st.plotly_chart(fig, use_container_width=True)

    # Capacity
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(y=res["cap"], mode="lines"))
    fig2.update_layout(title="Capacity Fade")
    st.plotly_chart(fig2, use_container_width=True)

    # Temp
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(y=res["temp"], mode="lines"))
    fig3.update_layout(title="Temperature")
    st.plotly_chart(fig3, use_container_width=True)