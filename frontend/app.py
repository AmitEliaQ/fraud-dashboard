import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import api_client
from api_client import BackendError

BG = "#0A0014"
PANEL_BG = "#170B2E"
GRID = "#2A1550"
CYAN = "#00F0FF"
PINK = "#FF2079"
GREEN = "#39FF14"
PURPLE = "#B026FF"

FILTER_KEYS = [
    "f_amount", "f_hour", "f_cat", "f_foreign", "f_mismatch",
    "f_trust", "f_vel", "f_age", "f_fraud",
]

st.set_page_config(page_title="FRAUD_DASHBOARD.exe", page_icon="🟣", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: 'Courier New', Courier, monospace !important;
    }
    .stApp {
        background-color: #0A0014;
        color: #00F0FF;
    }
    section[data-testid="stSidebar"] {
        background-color: #170B2E;
        border-right: 1px solid #FF2079;
    }
    section[data-testid="stSidebar"] * {
        font-family: 'Courier New', Courier, monospace !important;
    }
    h1, h2, h3, h4, h5 {
        color: #00F0FF !important;
        text-shadow: 0 0 8px rgba(255,32,121,0.7), 0 0 16px rgba(0,240,255,0.4);
        font-family: 'Courier New', Courier, monospace !important;
    }
    p, span, label, div, li {
        color: #00F0FF;
    }
    .terminal-banner {
        border: 1px solid #FF2079;
        padding: 18px 22px;
        margin-bottom: 22px;
        background: #170B2E;
        box-shadow: 0 0 24px rgba(255,32,121,0.35), 0 0 40px rgba(176,38,255,0.2);
    }
    .banner-title {
        font-size: 32px;
        font-weight: bold;
        letter-spacing: 3px;
        color: #FF2079;
        text-shadow: 0 0 10px #FF2079, 0 0 22px #B026FF, 0 0 34px #00F0FF;
    }
    .banner-sub {
        color: #B026FF;
        margin-top: 6px;
        font-size: 14px;
    }
    .cursor {
        color: #39FF14;
        animation: blink 1s step-start infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }
    [data-testid="stMetric"] {
        background-color: #170B2E;
        border: 1px solid #00F0FF;
        border-radius: 4px;
        padding: 12px;
        box-shadow: 0 0 10px rgba(0,240,255,0.2);
    }
    [data-testid="stMetricLabel"] {
        color: #B026FF !important;
    }
    [data-testid="stMetricValue"] {
        color: #FF2079 !important;
        text-shadow: 0 0 8px rgba(255,32,121,0.7);
    }
    hr {
        border-color: #B026FF !important;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #170B2E;
        color: #00F0FF;
        border: 1px solid #FF2079;
        font-family: 'Courier New', Courier, monospace;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #FF2079;
        color: #0A0014;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #00F0FF;
    }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #0A0014; }
    ::-webkit-scrollbar-thumb { background: #B026FF; }
    </style>
    """,
    unsafe_allow_html=True,
)


def neon_theme(fig, height=380, title=None):
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Courier New, monospace", color=CYAN),
        title=dict(text=title, font=dict(color=PINK)) if title else None,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=CYAN),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=CYAN),
        legend=dict(font=dict(color=CYAN), bgcolor="rgba(0,0,0,0)"),
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
    )
    return fig


@st.cache_data(ttl=60, show_spinner=False)
def load_health():
    return api_client.get_health()


@st.cache_data(ttl=600, show_spinner=False)
def load_meta():
    return api_client.get_meta()


@st.cache_data(ttl=600, show_spinner=False)
def load_transactions(filters):
    return api_client.get_transactions(filters)


@st.cache_data(ttl=600, show_spinner=False)
def load_predictive_features(filters):
    return api_client.get_predictive_features(filters)


def fetch(loader, *args):
    """Call the backend, or show the failure and end this script run."""
    with st.spinner("CONTACTING_BACKEND :: the first request can take about a minute"):
        try:
            return loader(*args)
        except BackendError as exc:
            st.error(f"!! BACKEND_UNAVAILABLE :: {exc}")
            st.stop()


health = fetch(load_health)
mismatch = api_client.environment_mismatch(health["environment"])
if mismatch:
    st.error(f"!! ENVIRONMENT_MISMATCH :: {mismatch}")
    st.stop()

meta = fetch(load_meta)

st.markdown(
    f"""
    <div class="terminal-banner">
        <div class="banner-title">FRAUD_DASHBOARD<span class="cursor">_</span></div>
        <div class="banner-sub">ENV :: {api_client.APP_ENV.upper()}</div>
        <div class="banner-sub">root@fraud-analytics:~$ ./analyze --dataset credit_card_fraud_10k.csv --mode interactive</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.markdown("### $ FILTERS")

if st.sidebar.button(">> RESET_FILTERS"):
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)
    st.rerun()

amount_bounds = tuple(meta["amount"])
amount_range = st.sidebar.slider(
    "AMOUNT ($)", amount_bounds[0], amount_bounds[1], amount_bounds, key="f_amount"
)

hour_range = st.sidebar.slider("TRANSACTION_HOUR", 0, 23, (0, 23), key="f_hour")

categories = meta["categories"]
selected_categories = st.sidebar.multiselect(
    "MERCHANT_CATEGORY", categories, default=categories, key="f_cat"
)

foreign_choice = st.sidebar.selectbox(
    "FOREIGN_TRANSACTION", ["ALL", "YES", "NO"], key="f_foreign"
)
mismatch_choice = st.sidebar.selectbox(
    "LOCATION_MISMATCH", ["ALL", "YES", "NO"], key="f_mismatch"
)

trust_bounds = tuple(meta["trust"])
trust_range = st.sidebar.slider(
    "DEVICE_TRUST_SCORE", trust_bounds[0], trust_bounds[1], trust_bounds, key="f_trust"
)

vel_bounds = tuple(meta["velocity"])
vel_range = st.sidebar.slider(
    "VELOCITY_LAST_24H", vel_bounds[0], vel_bounds[1], vel_bounds, key="f_vel"
)

age_bounds = tuple(meta["age"])
age_range = st.sidebar.slider(
    "CARDHOLDER_AGE", age_bounds[0], age_bounds[1], age_bounds, key="f_age"
)

fraud_choice = st.sidebar.selectbox(
    "FRAUD_STATUS", ["ALL", "FRAUD_ONLY", "LEGIT_ONLY"], key="f_fraud"
)

filters = {
    "amount": amount_range,
    "hour": hour_range,
    "categories": selected_categories,
    "foreign": foreign_choice,
    "mismatch": mismatch_choice,
    "trust": trust_range,
    "velocity": vel_range,
    "age": age_range,
    "fraud": fraud_choice,
}

result = fetch(load_transactions, filters)
filtered_df = pd.DataFrame(result["data"], columns=result["columns"])

if filtered_df.empty:
    st.warning("!! NO_RECORDS_FOUND :: adjust filters to widen the query")
    st.stop()

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
total = len(filtered_df)
fraud_count = int(filtered_df["is_fraud"].sum())
fraud_rate = fraud_count / total * 100
total_amount = filtered_df["amount"].sum()
fraud_amount = filtered_df.loc[filtered_df["is_fraud"] == 1, "amount"].sum()
avg_amount = filtered_df["amount"].mean()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("TOTAL_TX", f"{total:,}")
k2.metric("FRAUD_COUNT", f"{fraud_count:,}")
k3.metric("FRAUD_RATE", f"{fraud_rate:.2f}%")
k4.metric("TOTAL_VOLUME", f"${total_amount:,.2f}")
k5.metric("FRAUD_VOLUME", f"${fraud_amount:,.2f}")
k6.metric("AVG_TX_AMOUNT", f"${avg_amount:,.2f}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Feature predictiveness
# ---------------------------------------------------------------------------
st.markdown("## $ WHAT_PREDICTS_FRAUD.log")

features = fetch(load_predictive_features, filters)

if not features["sufficient"]:
    st.info(
        "!! INSUFFICIENT_CLASS_VARIANCE :: filtered set needs both fraud and "
        "legit examples (and at least 20 rows) to compute predictive features"
    )
else:
    fc1, fc2 = st.columns(2)

    corr = pd.DataFrame(features["correlation"])
    fig_corr = go.Figure(
        go.Bar(
            x=corr["value"],
            y=corr["feature"],
            orientation="h",
            marker_color=[GREEN if v >= 0 else PINK for v in corr["value"]],
        )
    )
    neon_theme(fig_corr, title="CORRELATION WITH is_fraud")
    fc1.plotly_chart(fig_corr, width="stretch")

    importances = pd.DataFrame(features["importance"])
    fig_rf = go.Figure(
        go.Bar(x=importances["value"], y=importances["feature"], orientation="h", marker_color=CYAN)
    )
    neon_theme(fig_rf, title="RANDOMFOREST FEATURE IMPORTANCE")
    fc2.plotly_chart(fig_rf, width="stretch")

st.markdown("---")

# ---------------------------------------------------------------------------
# Exploratory charts
# ---------------------------------------------------------------------------
st.markdown("## $ EXPLORATORY_ANALYSIS.log")

ec1, ec2 = st.columns(2)

cat_stats = filtered_df.groupby("merchant_category").agg(
    total=("is_fraud", "size"), fraud=("is_fraud", "sum")
)
cat_stats["fraud_rate"] = cat_stats["fraud"] / cat_stats["total"] * 100
fig_cat = go.Figure(
    go.Bar(x=cat_stats.index, y=cat_stats["fraud_rate"], marker_color=PINK)
)
neon_theme(fig_cat, title="FRAUD RATE (%) BY MERCHANT_CATEGORY")
ec1.plotly_chart(fig_cat, width="stretch")

hour_stats = filtered_df.groupby("transaction_hour").agg(
    total=("is_fraud", "size"), fraud=("is_fraud", "sum")
)
hour_stats["fraud_rate"] = hour_stats["fraud"] / hour_stats["total"] * 100
fig_hour = go.Figure(
    go.Bar(x=hour_stats.index, y=hour_stats["fraud_rate"], marker_color=PINK)
)
neon_theme(fig_hour, title="FRAUD RATE (%) BY TRANSACTION_HOUR")
ec2.plotly_chart(fig_hour, width="stretch")

ec3, ec4 = st.columns(2)

fig_amt = go.Figure()
fig_amt.add_trace(
    go.Histogram(
        x=filtered_df.loc[filtered_df["is_fraud"] == 0, "amount"],
        name="LEGIT",
        marker_color=CYAN,
        opacity=0.75,
    )
)
fig_amt.add_trace(
    go.Histogram(
        x=filtered_df.loc[filtered_df["is_fraud"] == 1, "amount"],
        name="FRAUD",
        marker_color=PINK,
        opacity=0.75,
    )
)
fig_amt.update_layout(barmode="overlay")
neon_theme(fig_amt, title="AMOUNT DISTRIBUTION :: FRAUD VS LEGIT")
ec3.plotly_chart(fig_amt, width="stretch")

fig_trust = go.Figure()
fig_trust.add_trace(
    go.Box(
        y=filtered_df.loc[filtered_df["is_fraud"] == 0, "device_trust_score"],
        name="LEGIT",
        marker_color=CYAN,
    )
)
fig_trust.add_trace(
    go.Box(
        y=filtered_df.loc[filtered_df["is_fraud"] == 1, "device_trust_score"],
        name="FRAUD",
        marker_color=PINK,
    )
)
neon_theme(fig_trust, title="DEVICE_TRUST_SCORE :: FRAUD VS LEGIT")
ec4.plotly_chart(fig_trust, width="stretch")

st.markdown("---")

# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------
st.markdown("## $ RAW_TRANSACTION_LOG")

tc1, tc2 = st.columns([3, 1])
columns = list(filtered_df.columns)
sort_by = tc1.selectbox("SORT_BY", options=columns, index=columns.index("amount"))
ascending = tc2.checkbox("ASCENDING", value=False)

sorted_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
st.caption(f"> {len(sorted_df):,} records matched :: sorted by {sort_by} ({'asc' if ascending else 'desc'})")
st.dataframe(sorted_df, width="stretch", height=420)

csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "DOWNLOAD_FILTERED_CSV",
    data=csv_bytes,
    file_name="filtered_fraud_data.csv",
    mime="text/csv",
)
