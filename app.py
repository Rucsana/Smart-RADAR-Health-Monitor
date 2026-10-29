import csv
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import serial
import serial.tools.list_ports
import streamlit as st

st.set_page_config(
    page_title="RADAR | Equipment Health",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- THEME ----------
st.markdown("""
<style>
    .stApp {
        background: #0b1120;
        color: #e5edf7;
    }
    [data-testid="stSidebar"] {
        background: #111a2d;
        border-right: 1px solid #26354d;
    }
    h1, h2, h3 {
        color: #eaf4ff !important;
    }
    p, label, span {
        color: #c6d3e4;
    }
    .hero {
        background: linear-gradient(120deg, #142541, #102b3b);
        border: 1px solid #294963;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 18px;
    }
    .hero-title {
        font-size: 27px;
        font-weight: 750;
        color: #f1f7ff;
    }
    .hero-subtitle {
        color: #9bb4ce;
        font-size: 14px;
        margin-top: 5px;
    }
    .section-label {
        color: #77d9ed;
        font-size: 12px;
        letter-spacing: 2px;
        font-weight: 700;
        margin: 12px 0 10px 0;
    }
    .status-box {
        padding: 17px 20px;
        border-radius: 12px;
        border: 1px solid #31425b;
        margin: 8px 0 18px 0;
    }
    .status-normal {
        background: #102c2b;
        border-color: #247e70;
    }
    .status-warning {
        background: #342916;
        border-color: #b88932;
    }
    .status-critical {
        background: #381c27;
        border-color: #bb475b;
    }
    .status-title {
        font-size: 20px;
        font-weight: 750;
    }
    .status-detail {
        color: #c1d0df;
        font-size: 13px;
        margin-top: 5px;
    }
    div[data-testid="stMetric"] {
        background: #121e32;
        border: 1px solid #293a54;
        padding: 16px;
        border-radius: 12px;
    }
    div[data-testid="stMetricLabel"] {
        color: #9db5cf;
    }
    div[data-testid="stMetricValue"] {
        color: #72d8ed;
    }
    div[data-testid="stPlotlyChart"] {
        background: #111a2b;
        border: 1px solid #26354d;
        border-radius: 12px;
        padding: 8px;
    }
    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 9px;
        font-weight: 650;
    }
    hr {
        border-color: #293a54;
    }
    .footer-note {
        color: #8298b3;
        font-size: 12px;
        text-align: center;
        padding: 16px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- CONSTANTS ----------
COLUMNS = [
    "time_ms", "ax", "ay", "az", "lm35_C",
    "dht_C", "humidity", "vibration_rms", "status"
]

NUMERIC_COLUMNS = [
    "time_ms", "ax", "ay", "az", "lm35_C",
    "dht_C", "humidity", "vibration_rms"
]

CHART_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

PLOT_STYLE = {
    "paper_bgcolor": "#111a2b",
    "plot_bgcolor": "#111a2b",
    "font": {"color": "#d7e5f5"},
    "margin": {"l": 15, "r": 15, "t": 55, "b": 15},
    "legend": {"orientation": "h", "y": 1.12},
    "xaxis": {
        "gridcolor": "#26354d",
        "zerolinecolor": "#26354d",
    },
    "yaxis": {
        "gridcolor": "#26354d",
        "zerolinecolor": "#26354d",
    },
}

# ---------- SESSION STATE ----------
defaults = {
    "radar_serial": None,
    "readings": [],
    "events": [],
    "last_status": None,
    "bad_lines": 0,
    "connection_message": "Not connected",
    "connection_error": "",
    "sample_count": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def parse_line(line):
    try:
        parts = next(csv.reader([line.strip()]))

        if len(parts) != len(COLUMNS):
            return None

        if parts[0].strip().lower() == "time_ms":
            return None

        row = dict(zip(COLUMNS, parts))

        for col in NUMERIC_COLUMNS:
            row[col] = float(row[col].strip())

        row["status"] = row["status"].strip().upper()

        if not row["status"]:
            return None

        row["received_at"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return row

    except (ValueError, csv.Error, StopIteration):
        return None


def record_event(status, message):
    st.session_state.events.append({
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Status": status,
        "Event": message,
    })
    st.session_state.events = st.session_state.events[-200:]


def styled_chart(fig, height=300):
    fig.update_layout(**PLOT_STYLE, height=height)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=CHART_CONFIG,
    )


# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("## 📡 RADAR MONITOR")
    st.caption("EQUIPMENT HEALTH CONSOLE")
    st.divider()

    st.markdown("### Connection")

    ports = sorted({
        p.device for p in serial.tools.list_ports.comports()
    })
    options = sorted(set(ports + ["COM4"]))

    selected_port = st.selectbox(
        "Serial port",
        options=options,
        index=options.index("COM4"),
    )

    baud_rate = st.selectbox(
        "Baud rate",
        [115200, 9600, 57600, 38400],
        index=0,
    )

    if st.button("Connect to ESP32", use_container_width=True):
        try:
            current = st.session_state.radar_serial
            if current is not None:
                current.close()

            connection = serial.Serial(
                selected_port,
                baudrate=baud_rate,
                timeout=0.1,
            )

            time.sleep(1)
            connection.reset_input_buffer()

            st.session_state.radar_serial = connection
            st.session_state.connection_message = (
                f"Connected to {selected_port}"
            )
            st.session_state.connection_error = ""
            record_event("INFO", f"Serial connected: {selected_port}")

        except (serial.SerialException, OSError) as exc:
            st.session_state.radar_serial = None
            st.session_state.connection_error = str(exc)
            st.session_state.connection_message = "Connection failed"

    if st.button("Disconnect", use_container_width=True):
        connection = st.session_state.radar_serial

        if connection is not None:
            try:
                connection.close()
            except (serial.SerialException, OSError):
                pass

        st.session_state.radar_serial = None
        st.session_state.connection_message = "Disconnected"
        record_event("INFO", "Serial disconnected")

    connection = st.session_state.radar_serial
    is_connected = (
        connection is not None and connection.is_open
    )

    if is_connected:
        st.success(st.session_state.connection_message)
    else:
        st.warning(st.session_state.connection_message)

    if st.session_state.connection_error:
        st.error(st.session_state.connection_error)

    st.divider()
    st.markdown("### Demo alert thresholds")
    st.caption("Adjust these for your prototype demonstration.")

    vibration_limit = st.number_input(
        "Vibration RMS (m/s²)",
        min_value=0.0,
        value=0.8,
        step=0.1,
    )
    temperature_limit = st.number_input(
        "LM35 temperature (°C)",
        min_value=0.0,
        value=40.0,
        step=1.0,
    )
    ambient_limit = st.number_input(
        "Ambient temperature (°C)",
        min_value=0.0,
        value=40.0,
        step=1.0,
    )

    st.divider()
    st.caption("LOCAL PROTOTYPE • USB SERIAL • NO CLOUD REQUIRED")


# ---------- READ SERIAL DATA ----------
connection = st.session_state.radar_serial

if connection is not None and connection.is_open:
    try:
        for _ in range(200):
            if connection.in_waiting <= 0:
                break

            line = connection.readline().decode(
                "utf-8", errors="ignore"
            ).strip()

            if not line:
                continue

            row = parse_line(line)

            if row is None:
                st.session_state.bad_lines += 1
                continue

            st.session_state.readings.append(row)
            st.session_state.readings = (
                st.session_state.readings[-1000:]
            )
            st.session_state.sample_count += 1

    except (serial.SerialException, OSError) as exc:
        st.session_state.connection_error = str(exc)
        st.session_state.radar_serial = None
        record_event("ERROR", "Serial connection lost")


# ---------- ASSESS CURRENT STATUS ----------
df = pd.DataFrame(st.session_state.readings)

dashboard_status = None
status_reason = "Waiting for valid sensor data"

if not df.empty:
    latest = df.iloc[-1]
    firmware_status = str(latest["status"]).upper()

    warning_reasons = []

    if latest["vibration_rms"] >= vibration_limit:
        warning_reasons.append("Vibration above demo threshold")

    if latest["lm35_C"] >= temperature_limit:
        warning_reasons.append("LM35 temperature above demo threshold")

    if latest["dht_C"] >= ambient_limit:
        warning_reasons.append("Ambient temperature above demo threshold")

    if firmware_status in ("CRITICAL", "ALERT"):
        dashboard_status = "CRITICAL"
        status_reason = f"Firmware reports {firmware_status}"
    elif firmware_status in ("WARNING", "DEGRADATION"):
        dashboard_status = "WARNING"
        status_reason = f"Firmware reports {firmware_status}"
    elif warning_reasons:
        dashboard_status = "WARNING"
        status_reason = "; ".join(warning_reasons)
    else:
        dashboard_status = "NORMAL"
        status_reason = "No configured demo threshold exceeded"

    previous_status = st.session_state.last_status

    if dashboard_status != previous_status:
        record_event(dashboard_status, status_reason)
        st.session_state.last_status = dashboard_status


# ---------- HEADER ----------
st.markdown("""
<div class="hero">
    <div class="hero-title">Smart RADAR Equipment Health</div>
    <div class="hero-subtitle">
        REAL-TIME CONDITION MONITORING &nbsp; • &nbsp;
        VIBRATION &nbsp; • &nbsp; TEMPERATURE &nbsp; • &nbsp; HUMIDITY
    </div>
</div>
""", unsafe_allow_html=True)

# Header status strip
header_left, header_right = st.columns([3, 1])

with header_left:
    st.markdown(
        '<div class="section-label">SYSTEM OVERVIEW</div>',
        unsafe_allow_html=True,
    )

with header_right:
    if is_connected:
        st.markdown("**🟢 SERIAL ONLINE**")
    else:
        st.markdown("**⚪ SERIAL OFFLINE**")


# ---------- STATUS PANEL ----------
if dashboard_status is None:
    st.info(
        "Waiting for sensor data. Connect the ESP32 and check "
        "that its firmware is transmitting the expected CSV format."
    )
else:
    css_class = {
        "NORMAL": "status-normal",
        "WARNING": "status-warning",
        "CRITICAL": "status-critical",
    }[dashboard_status]

    symbol = {
        "NORMAL": "🟢",
        "WARNING": "🟡",
        "CRITICAL": "🔴",
    }[dashboard_status]

    st.markdown(f"""
    <div class="status-box {css_class}">
        <div class="status-title">
            {symbol} EQUIPMENT STATUS: {dashboard_status}
        </div>
        <div class="status-detail">{status_reason}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------- LIVE METRICS ----------
st.markdown(
    '<div class="section-label">LIVE SENSOR TELEMETRY</div>',
    unsafe_allow_html=True,
)

if not df.empty:
    latest = df.iloc[-1]

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "〰️ Vibration RMS",
        f"{latest['vibration_rms']:.3f} m/s²",
    )
    m2.metric(
        "🌡️ Equipment temp.",
        f"{latest['lm35_C']:.1f} °C",
    )
    m3.metric(
        "🌡️ Ambient temp.",
        f"{latest['dht_C']:.1f} °C",
    )
    m4.metric(
        "💧 Relative humidity",
        f"{latest['humidity']:.1f} %",
    )

    st.caption(
        f"Last received: {latest['received_at']}  •  "
        f"ESP32 uptime: {latest['time_ms']:.0f} ms  •  "
        f"Valid samples: {len(df)}"
    )

    # ---------- GRAPHS ----------
    st.markdown(
        '<div class="section-label">PERFORMANCE TRENDS</div>',
        unsafe_allow_html=True,
    )

    chart_df = df.copy()

    # Handle ESP32 uptime counter resetting after a reboot.
    # Use laptop receive timestamps as the continuous chart axis.
    chart_df["received_at"] = pd.to_datetime(
        chart_df["received_at"]
    )
    chart_df["elapsed_seconds"] = (
        chart_df["received_at"] - chart_df["received_at"].iloc[0]
    ).dt.total_seconds()

    left, right = st.columns(2)

    with left:
        fig = px.line(
            chart_df,
            x="elapsed_seconds",
            y="vibration_rms",
            title="Vibration RMS",
            labels={
                "elapsed_seconds": "Elapsed time (s)",
                "vibration_rms": "RMS (m/s²)",
            },
        )
        fig.add_hline(
            y=vibration_limit,
            line_dash="dash",
            line_color="#f4bd50",
            annotation_text="Demo warning level",
        )
        styled_chart(fig)

    with right:
        temp_df = chart_df.melt(
            id_vars=["elapsed_seconds"],
            value_vars=["lm35_C", "dht_C"],
            var_name="Sensor",
            value_name="Temperature (°C)",
        )
        temp_df["Sensor"] = temp_df["Sensor"].map({
            "lm35_C": "LM35 equipment",
            "dht_C": "DHT22 ambient",
        })

        fig = px.line(
            temp_df,
            x="elapsed_seconds",
            y="Temperature (°C)",
            color="Sensor",
            title="Temperature trends",
        )
        fig.add_hline(
            y=temperature_limit,
            line_dash="dash",
            line_color="#f4bd50",
            annotation_text="LM35 demo warning level",
        )
        styled_chart(fig)

    left, right = st.columns(2)

    with left:
        acceleration_df = chart_df.melt(
            id_vars=["elapsed_seconds"],
            value_vars=["ax", "ay", "az"],
            var_name="Axis",
            value_name="Acceleration (m/s²)",
        )

        fig = px.line(
            acceleration_df,
            x="elapsed_seconds",
            y="Acceleration (m/s²)",
            color="Axis",
            title="MPU6050 · Three-axis acceleration",
        )
        styled_chart(fig)

    with right:
        fig = px.line(
            chart_df,
            x="elapsed_seconds",
            y="humidity",
            title="Ambient relative humidity",
            labels={"humidity": "Humidity (%)"},
        )
        styled_chart(fig)

    # ---------- EVENT HISTORY ----------
    st.markdown(
        '<div class="section-label">STATUS & EVENT HISTORY</div>',
        unsafe_allow_html=True,
    )

    events_df = pd.DataFrame(st.session_state.events)

    if events_df.empty:
        st.caption("No status changes recorded yet.")
    else:
        st.dataframe(
            events_df.iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

    # ---------- RAW DATA ----------
    with st.expander("View recent raw sensor readings"):
        st.dataframe(
            df.tail(25).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

    download_col, clear_col = st.columns([2, 1])

    with download_col:
        st.download_button(
            "⬇️ Export sensor data (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="radar_health_readings.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with clear_col:
        if st.button(
            "Clear session data",
            use_container_width=True,
        ):
            st.session_state.readings = []
            st.session_state.events = []
            st.session_state.last_status = None
            st.session_state.sample_count = 0
            st.rerun()

else:
    st.markdown("""
    <div class="status-box">
        <div class="status-title">📥 Awaiting telemetry</div>
        <div class="status-detail">
            Once valid ESP32 readings arrive, the sensor cards,
            performance graphs and event history will appear here.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="footer-note">
    SMART RADAR EQUIPMENT HEALTH MONITORING · STUDENT PROTOTYPE
    <br>
    Demonstration thresholds only — not certified equipment diagnostics.
</div>
""", unsafe_allow_html=True)

# Refresh automatically when connected.
# The short pause also gives the serial reader time to receive data.
if (
    st.session_state.radar_serial is not None
    and st.session_state.radar_serial.is_open
):
    time.sleep(0.5)
    st.rerun()