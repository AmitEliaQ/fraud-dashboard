import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier

DATA_PATH = "credit_card_fraud_10k.csv"

BG = "#0D0208"
PANEL_BG = "#0A1F0D"
GREEN = "#00FF41"
DIM_GREEN = "#008F11"
GRID = "#123317"

FEATURE_COLS = [
    "amount",
    "transaction_hour",
    "foreign_transaction",
    "location_mismatch",
    "device_trust_score",
    "velocity_last_24h",
    "cardholder_age",
]

FILTER_KEYS = [
    "f_amount", "f_hour", "f_cat", "f_foreign", "f_mismatch",
    "f_trust", "f_vel", "f_age", "f_fraud",
]

st.set_page_config(page_title="FRAUD_DASHBOARD.exe", page_icon="🟢", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: 'Courier New', Courier, monospace !important;
    }
    .stApp {
        background-color: #0D0208;
        color: #00FF41;
    }
    section[data-testid="stSidebar"] {
        background-color: #0A1F0D;
        border-right: 1px solid #00FF41;
    }
    section[data-testid="stSidebar"] * {
        font-family: 'Courier New', Courier, monospace !important;
    }
    h1, h2, h3, h4, h5 {
        color: #00FF41 !important;
        text-shadow: 0 0 8px rgba(0,255,65,0.6);
        font-family: 'Courier New', Courier, monospace !important;
    }
    p, span, label, div, li {
        color: #00FF41;
    }
    .terminal-banner {
        border: 1px solid #00FF41;
        padding: 18px 22px;
        margin-bottom: 22px;
        background: #0A1F0D;
        box-shadow: 0 0 18px rgba(0,255,65,0.25);
    }
    .banner-title {
        font-size: 32px;
        font-weight: bold;
        letter-spacing: 3px;
        text-shadow: 0 0 10px #00FF41, 0 0 22px #00FF41;
    }
    .banner-sub {
        color: #008F11;
        margin-top: 6px;
        font-size: 14px;
    }
    .cursor {
        animation: blink 1s step-start infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }
    [data-testid="stMetric"] {
        background-color: #0A1F0D;
        border: 1px solid #00FF41;
        border-radius: 4px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"] {
        color: #008F11 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00FF41 !important;
        text-shadow: 0 0 6px rgba(0,255,65,0.6);
    }
    hr {
        border-color: #00FF41 !important;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #0A1F0D;
        color: #00FF41;
        border: 1px solid #00FF41;
        font-family: 'Courier New', Courier, monospace;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #00FF41;
        color: #0D0208;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #00FF41;
    }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #0D0208; }
    ::-webkit-scrollbar-thumb { background: #008F11; }
    </style>
    """,
    unsafe_allow_html=True,
)


def matrix_theme(fig, height=380, title=None):
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Courier New, monospace", color=GREEN),
        title=dict(text=title, font=dict(color=GREEN)) if title else None,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=GREEN),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=GREEN),
        legend=dict(font=dict(color=GREEN), bgcolor="rgba(0,0,0,0)"),
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
    )
    return fig


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


df = load_data()

st.markdown(
    """
    <div class="terminal-banner">
        <div class="banner-title">FRAUD_DASHBOARD<span class="cursor">_</span></div>
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

amount_bounds = (float(df["amount"].min()), float(df["amount"].max()))
amount_range = st.sidebar.slider(
    "AMOUNT ($)", amount_bounds[0], amount_bounds[1], amount_bounds, key="f_amount"
)

hour_range = st.sidebar.slider("TRANSACTION_HOUR", 0, 23, (0, 23), key="f_hour")

categories = sorted(df["merchant_category"].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "MERCHANT_CATEGORY", categories, default=categories, key="f_cat"
)

foreign_choice = st.sidebar.selectbox(
    "FOREIGN_TRANSACTION", ["ALL", "YES", "NO"], key="f_foreign"
)
mismatch_choice = st.sidebar.selectbox(
    "LOCATION_MISMATCH", ["ALL", "YES", "NO"], key="f_mismatch"
)

trust_bounds = (int(df["device_trust_score"].min()), int(df["device_trust_score"].max()))
trust_range = st.sidebar.slider(
    "DEVICE_TRUST_SCORE", trust_bounds[0], trust_bounds[1], trust_bounds, key="f_trust"
)

vel_bounds = (int(df["velocity_last_24h"].min()), int(df["velocity_last_24h"].max()))
vel_range = st.sidebar.slider(
    "VELOCITY_LAST_24H", vel_bounds[0], vel_bounds[1], vel_bounds, key="f_vel"
)

age_bounds = (int(df["cardholder_age"].min()), int(df["cardholder_age"].max()))
age_range = st.sidebar.slider(
    "CARDHOLDER_AGE", age_bounds[0], age_bounds[1], age_bounds, key="f_age"
)

fraud_choice = st.sidebar.selectbox(
    "FRAUD_STATUS", ["ALL", "FRAUD_ONLY", "LEGIT_ONLY"], key="f_fraud"
)

mask = (
    df["amount"].between(*amount_range)
    & df["transaction_hour"].between(*hour_range)
    & df["merchant_category"].isin(selected_categories)
    & df["device_trust_score"].between(*trust_range)
    & df["velocity_last_24h"].between(*vel_range)
    & df["cardholder_age"].between(*age_range)
)
if foreign_choice != "ALL":
    mask &= df["foreign_transaction"] == (1 if foreign_choice == "YES" else 0)
if mismatch_choice != "ALL":
    mask &= df["location_mismatch"] == (1 if mismatch_choice == "YES" else 0)
if fraud_choice != "ALL":
    mask &= df["is_fraud"] == (1 if fraud_choice == "FRAUD_ONLY" else 0)

filtered_df = df[mask]

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

cat_dummies = pd.get_dummies(filtered_df["merchant_category"], prefix="cat")
X = pd.concat([filtered_df[FEATURE_COLS], cat_dummies], axis=1)
y = filtered_df["is_fraud"]

if len(filtered_df) < 20 or y.nunique() < 2:
    st.info(
        "!! INSUFFICIENT_CLASS_VARIANCE :: filtered set needs both fraud and "
        "legit examples (and at least 20 rows) to compute predictive features"
    )
else:
    fc1, fc2 = st.columns(2)

    corr = X.assign(is_fraud=y).corr(numeric_only=True)["is_fraud"].drop("is_fraud")
    corr = corr.sort_values(key=lambda s: s.abs())
    fig_corr = go.Figure(
        go.Bar(
            x=corr.values,
            y=corr.index,
            orientation="h",
            marker_color=[GREEN if v >= 0 else DIM_GREEN for v in corr.values],
        )
    )
    matrix_theme(fig_corr, title="CORRELATION WITH is_fraud")
    fc1.plotly_chart(fig_corr, use_container_width=True)

    rf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    rf.fit(X, y)
    importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values()
    fig_rf = go.Figure(
        go.Bar(x=importances.values, y=importances.index, orientation="h", marker_color=GREEN)
    )
    matrix_theme(fig_rf, title="RANDOMFOREST FEATURE IMPORTANCE")
    fc2.plotly_chart(fig_rf, use_container_width=True)

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
    go.Bar(x=cat_stats.index, y=cat_stats["fraud_rate"], marker_color=GREEN)
)
matrix_theme(fig_cat, title="FRAUD RATE (%) BY MERCHANT_CATEGORY")
ec1.plotly_chart(fig_cat, use_container_width=True)

hour_stats = filtered_df.groupby("transaction_hour").agg(
    total=("is_fraud", "size"), fraud=("is_fraud", "sum")
)
hour_stats["fraud_rate"] = hour_stats["fraud"] / hour_stats["total"] * 100
fig_hour = go.Figure(
    go.Bar(x=hour_stats.index, y=hour_stats["fraud_rate"], marker_color=GREEN)
)
matrix_theme(fig_hour, title="FRAUD RATE (%) BY TRANSACTION_HOUR")
ec2.plotly_chart(fig_hour, use_container_width=True)

ec3, ec4 = st.columns(2)

fig_amt = go.Figure()
fig_amt.add_trace(
    go.Histogram(
        x=filtered_df.loc[filtered_df["is_fraud"] == 0, "amount"],
        name="LEGIT",
        marker_color=DIM_GREEN,
        opacity=0.75,
    )
)
fig_amt.add_trace(
    go.Histogram(
        x=filtered_df.loc[filtered_df["is_fraud"] == 1, "amount"],
        name="FRAUD",
        marker_color=GREEN,
        opacity=0.75,
    )
)
fig_amt.update_layout(barmode="overlay")
matrix_theme(fig_amt, title="AMOUNT DISTRIBUTION :: FRAUD VS LEGIT")
ec3.plotly_chart(fig_amt, use_container_width=True)

fig_trust = go.Figure()
fig_trust.add_trace(
    go.Box(
        y=filtered_df.loc[filtered_df["is_fraud"] == 0, "device_trust_score"],
        name="LEGIT",
        marker_color=DIM_GREEN,
    )
)
fig_trust.add_trace(
    go.Box(
        y=filtered_df.loc[filtered_df["is_fraud"] == 1, "device_trust_score"],
        name="FRAUD",
        marker_color=GREEN,
    )
)
matrix_theme(fig_trust, title="DEVICE_TRUST_SCORE :: FRAUD VS LEGIT")
ec4.plotly_chart(fig_trust, use_container_width=True)

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
st.dataframe(sorted_df, use_container_width=True, height=420)

csv_bytes = sorted_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "DOWNLOAD_FILTERED_CSV",
    data=csv_bytes,
    file_name="filtered_fraud_data.csv",
    mime="text/csv",
)
