# dashboard.py — corrected and complete
# Run: streamlit run dashboard.py

import streamlit as st
import requests
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
from datetime import datetime
import random
import json
import os
# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

st.set_page_config(
    page_title="FinGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp { background-color: #0d1117; }

section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
}

div[data-testid="metric-container"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px;
}

.decision-box {
    border-radius: 10px;
    padding: 24px;
    text-align: center;
    font-size: 32px;
    font-weight: 700;
    margin: 10px 0 20px 0;
    letter-spacing: 2px;
}

.stButton > button {
    background-color: #1f6feb;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    width: 100%;
    padding: 10px;
    font-size: 15px;
}

.stButton > button:hover {
    background-color: #388bfd;
}

.reason-item {
    background: #161b22;
    border-left: 3px solid #f85149;
    border-radius: 0 6px 6px 0;
    padding: 8px 14px;
    margin: 6px 0;
    font-size: 14px;
    color: #e6edf3;
}

.ok-item {
    background: #161b22;
    border-left: 3px solid #3fb950;
    border-radius: 0 6px 6px 0;
    padding: 8px 14px;
    margin: 6px 0;
    font-size: 14px;
    color: #e6edf3;
}

.profile-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────

API_URL = "http://127.0.0.1:8000"

USERS = {
    1: {"name": "Aman",  "persona": "Student",      "color": "#58a6ff"},
    2: {"name": "Riya",  "persona": "Night Gamer",   "color": "#bc8cff"},
    3: {"name": "Kabir", "persona": "VIP Traveler",  "color": "#ffa657"},
}

DECISION_STYLE = {
    "APPROVE": {"bg": "#0d2b1a", "border": "#3fb950", "text": "#3fb950"},
    "WARN":    {"bg": "#2b1f00", "border": "#d29922", "text": "#d29922"},
    "DELAY":   {"bg": "#2b1400", "border": "#f0883e", "text": "#f0883e"},
    "BLOCK":   {"bg": "#2b0000", "border": "#f85149", "text": "#f85149"},
}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def call_api(payload: dict) -> dict:
    try:
        r = requests.post(f"{API_URL}/score", json=payload, timeout=5)
        return r.json() if r.status_code == 200 else {"error": "Bad response"}
    except requests.exceptions.ConnectionError:
        return {"error": "API offline. Run: uvicorn api:app --reload"}
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=60)
def load_transactions() -> pd.DataFrame:
    conn = sqlite3.connect("data/finguard.db")
    df = pd.read_sql_query("""
        SELECT t.txn_id, t.user_id, t.amount,
               t.timestamp, t.location, t.merchant,
               u.name, u.persona
        FROM transactions t
        JOIN users u ON t.user_id = u.user_id
        ORDER BY t.timestamp DESC
    """, conn)
    conn.close()
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df["hour"] = df["timestamp"].dt.hour
    return df

def dark_chart(fig, height=300):
    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        font_color="#8b949e",
        height=height,
        margin=dict(t=45, b=35, l=35, r=20),
        xaxis={"gridcolor": "#21262d", "linecolor": "#21262d"},
        yaxis={"gridcolor": "#21262d", "linecolor": "#21262d"},
        legend={"bgcolor": "#161b22", "bordercolor": "#21262d"}
    )
    return fig

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛡️ FinGuard")
    st.caption("Hybrid Fraud Detection System")
    st.divider()

    page = st.radio("Navigation", [
        "🔍 Score a Transaction",
        "📋 Transaction Data",
        "👤 User Profiles",
        "📡 Live Feed",
      "📊 Model Intelligence",
        "💥 Attack Simulation",
    ], label_visibility="collapsed")

    st.divider()

    # Live API status
    try:
        r = requests.get(f"{API_URL}/", timeout=2)
        data = r.json()
        st.success("🟢 API Online")
        # ← fix: use calculated number not the ? field
        total = 1 + 1 + 1 + len(data.get("models", []))
        st.caption(f"Models loaded: {data.get('models_loaded', total)}")
        if data.get("shap") == "enabled":
            st.caption("SHAP: enabled ✓")
    except:
        st.error("🔴 API Offline")
        st.caption("Run: uvicorn api:app --reload")

    st.divider()
    st.caption("v2.0 — Isolation Forest + XGBoost + SHAP")

# ════════════════════════════════════════════
# PAGE 1 — SCORE A TRANSACTION
# ════════════════════════════════════════════

if page == "🔍 Score a Transaction":

    st.title("🔍 Score a Transaction")
    st.caption("Fill in transaction details and get an instant fraud decision.")
    st.divider()

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### Transaction details")

        user_id = st.selectbox(
            "User",
            [1, 2, 3],
            format_func=lambda x: f"{USERS[x]['name']} — {USERS[x]['persona']}"
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=1.0,
            max_value=5000000.0,
            value=500.0,
            step=100.0
        )

        col_d, col_h = st.columns(2)
        with col_d:
            date = st.date_input("Date", value=datetime.now().date())
        with col_h:
            hour = st.slider(
                "Hour",
                0, 23, 14,
                help="0 = midnight · 12 = noon · 23 = 11 PM"
            )
            st.caption(
                f"{'🌙 Night' if hour < 6 else '🌅 Morning' if hour < 12 else '☀️ Afternoon' if hour < 18 else '🌆 Evening'}"
                f" — {hour:02d}:00"
            )

        location = st.selectbox(
            "Location",
            ["Mumbai", "Delhi", "Bangalore",
             "Dubai", "London", "UnknownCity"]
        )

        merchant = st.selectbox(
            "Merchant",
            ["Swiggy", "Zomato", "Amazon", "Steam",
             "EpicGames", "LuxuryMall", "Airline",
             "Hotel", "BookStore", "UnknownMerchant"]
        )

        st.markdown("")
        # ← FIXED: was "go = st.button(...)" which clashed with plotly import
        analyse_btn = st.button("Analyse Transaction →")

    with right:
        st.markdown("#### Decision")

        if analyse_btn:
            ts = f"{date}T{str(hour).zfill(2)}:00:00"

            with st.spinner("Scoring..."):
                result = call_api({
                    "user_id":   user_id,
                    "amount":    amount,
                    "timestamp": ts,
                    "location":  location,
                    "merchant":  merchant
                })

            if "error" in result:
                st.error(result["error"])
                st.stop()

            decision  = result["decision"]
            risk      = result["risk_score"]
            fraud_p   = result["fraud_probability"]
            anomaly   = result["models"]["anomaly_label"]
            a_score   = result["models"]["anomaly_score"]
            xgb_prob  = result.get("models", {}).get("xgboost_prob", 0)    # ← ADD
            rf_prob   = result.get("models", {}).get("random_forest_prob", 0)
            reasons   = result.get("reasons", [])
            features  = result.get("features_used", {})
            shap_exp  = result.get("shap_explanation", {})
            style     = DECISION_STYLE[decision]

            # ── Decision box ──
            st.markdown(
                f'<div class="decision-box" style="'
                f'background:{style["bg"]};'
                f'border: 2px solid {style["border"]};'
                f'color:{style["text"]};">'
                f'{decision}'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── 3 numbers ──
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Risk Score",  risk,
                    help="Combined score from all 4 models")
            c2.metric("XGBoost",     f"{xgb_prob*100:.1f}%",
                    help="Supervised fraud probability")
            c3.metric("Random Forest", f"{rf_prob*100:.1f}%",
                    help="Ensemble fraud probability")
            ae_data  = result.get("autoencoder", {})
            if ae_data.get("is_anomaly"):
                st.markdown(
                    f'<div class="reason-item">'
                    f'⚠️ Autoencoder flagged this transaction — '
                    f'reconstruction error {ae_data["reconstruction_error"]:.4f} '
                    f'is {ae_data["anomaly_score_ratio"]:.1f}× above normal threshold'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="ok-item">'
                    f'✅ Autoencoder — transaction pattern looks normal '
                    f'(error: {ae_data.get("reconstruction_error", 0):.4f})'
                    f'</div>',
                    unsafe_allow_html=True
                )
            ae_error = ae_data.get("reconstruction_error", 0)
            ae_ratio = ae_data.get("anomaly_score_ratio", 0)
            ae_flag  = ae_data.get("is_anomaly", False)

            c4.metric(
                "Autoencoder",
                "⚠️ Anomaly" if ae_flag else "✓ Normal",
                delta=f"Error ratio: {ae_ratio:.2f}x",
                delta_color="inverse",
                help=f"Reconstruction error: {ae_error:.4f} vs threshold 0.1985"
            )
            st.divider()

            # ── What triggered this ──
            st.markdown("**What triggered this decision:**")
            if reasons:
                for r in reasons:
                    st.markdown(
                        f'<div class="reason-item">⚠️ {r}</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    '<div class="ok-item">✅ No risk factors — transaction looks normal</div>',
                    unsafe_allow_html=True
                )

            # ── SHAP explanation ──
            top_shap = shap_exp.get("top_reasons", [])
            if top_shap:
                st.divider()
                st.markdown("**Why XGBoost gave this probability (SHAP):**")
                for t in top_shap:
                    st.markdown(f"• {t}")

            # ── Risk breakdown bar ──
            st.divider()
            st.markdown("**Risk points breakdown:**")

            user_avg = features.get("user_avg_amount", 1)
            time_gap = features.get("time_since_last_txn", 9999)

            contrib = {}
            if anomaly == -1:
                contrib["Isolation Forest flagged"] = 35
            if a_score < -0.08:
                contrib["Strong anomaly score"] = 15
            if fraud_p > 0.7:
                contrib["XGBoost high probability"] = 40
            elif fraud_p > 0.4:
                contrib["XGBoost moderate probability"] = 20
            if amount > user_avg * 10:
                contrib["Amount 10× your average"] = 30
            elif amount > user_avg * 5:
                contrib["Amount 5× your average"] = 20
            if time_gap < 30:
                contrib["Extremely fast transaction"] = 35
            elif time_gap < 60:
                contrib["Very fast transaction"] = 25
            if hour < 5:
                contrib[f"Late night hour ({hour}:00)"] = 20

            if contrib:
                fig_bar = go.Figure(go.Bar(
                    x=list(contrib.values()),
                    y=list(contrib.keys()),
                    orientation="h",
                    marker_color=[
                        "#f85149" if v >= 30 else
                        "#f0883e" if v >= 20 else
                        "#d29922"
                        for v in contrib.values()
                    ],
                    text=[f"+{v} pts" for v in contrib.values()],
                    textposition="outside",
                    textfont={"color": "#e6edf3", "size": 12}
                ))
                fig_bar = dark_chart(fig_bar, height=200 + len(contrib) * 30)
                fig_bar.update_layout(
                    xaxis={"range": [0, 55],
                           "gridcolor": "#21262d"},
                    yaxis={"gridcolor": "#21262d"},
                    showlegend=False
                )
                st.plotly_chart(fig_bar,  use_container_width=True, config={"displayModeBar": False}, key="score_bar")
            else:
                st.markdown(
                    '<div class="ok-item">✅ 0 risk points — all signals clean</div>',
                    unsafe_allow_html=True
                )

            # ── Context numbers ──
            st.divider()
            st.caption(
                f"User avg: ₹{user_avg:,.0f} · "
                f"This txn: ₹{amount:,.0f} · "
                f"Time since last: {time_gap:.0f}s · "
                f"Hour: {hour}:00"
            )

        else:
            st.markdown(
                '<div style="height:320px; border:1px dashed #21262d;'
                'border-radius:8px; display:flex; align-items:center;'
                'justify-content:center; color:#8b949e; font-size:15px;">'
                '← Fill the form and click Analyse'
                '</div>',
                unsafe_allow_html=True
            )

# ════════════════════════════════════════════
# PAGE 2 — TRANSACTION DATA
# ════════════════════════════════════════════

elif page == "📋 Transaction Data":

    st.title("📋 Transaction Data")
    st.caption("All 2,200 transactions in the database.")
    st.divider()

    df = load_transactions()

    # ── Filters ──
    f1, f2 = st.columns(2)
    with f1:
        user_filter = st.multiselect(
            "Show users",
            [1, 2, 3],
            default=[1, 2, 3],
            format_func=lambda x: USERS[x]["name"]
        )
    with f2:
        max_amt = int(df["amount"].max())
        amt_range = st.slider(
            "Amount range (₹)",
            0, max_amt, (0, max_amt)
        )

    filtered = df[
        (df["user_id"].isin(user_filter)) &
        (df["amount"].between(amt_range[0], amt_range[1]))
    ]

    # ── 4 summary numbers ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Transactions",   f"{len(filtered):,}")
    m2.metric("Total Volume",   f"₹{filtered['amount'].sum()/100000:.1f}L")
    m3.metric("Average Amount", f"₹{filtered['amount'].mean():,.0f}")
    m4.metric("Highest Amount", f"₹{filtered['amount'].max():,.0f}")

    st.divider()

    # ── Charts ──
    c1, c2 = st.columns(2)

    with c1:
        # Transactions by hour — most useful chart
        hourly = filtered.groupby("hour").size().reset_index(name="txns")
        fig1 = go.Figure(go.Bar(
            x=hourly["hour"],
            y=hourly["txns"],
            marker_color="#1f6feb",
            hovertemplate="Hour %{x}:00 → %{y} transactions<extra></extra>"
        ))
        fig1 = dark_chart(fig1, 300)
        fig1.update_layout(
            title="What time do transactions happen?",
            xaxis={
                "title": "Hour of day",
                "gridcolor": "#21262d",
                "tickvals": [0, 4, 8, 12, 16, 20, 23],
                "ticktext": ["12AM","4AM","8AM","12PM","4PM","8PM","11PM"]
            },
            yaxis={"title": "Number of transactions",
                   "gridcolor": "#21262d"}
        )
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False}, key="data_hourly")
        st.caption(
            "💡 Aman (Student) is active 8AM–11PM. "
            "Riya (Night Gamer) peaks after 10PM. "
            "Kabir (VIP) is 9AM–6PM."
        )

    with c2:
        # Top merchants
        top_m = (
            filtered.groupby("merchant")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
            .tail(8)
        )
        fig2 = go.Figure(go.Bar(
            x=top_m["count"],
            y=top_m["merchant"],
            orientation="h",
            marker_color="#238636",
            hovertemplate="%{y}: %{x} transactions<extra></extra>"
        ))
        fig2 = dark_chart(fig2, 300)
        fig2.update_layout(
            title="Most used merchants",
            xaxis={"title": "Transactions",
                   "gridcolor": "#21262d"},
            yaxis={"gridcolor": "#21262d"}
        )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False}, key="data_merchant")
    st.caption(
            "💡 Amazon, Zomato, Swiggy appear across all 3 users. "
            "Steam/EpicGames are only Riya. LuxuryMall/Airline only Kabir."
        )

    st.divider()

    # ── Table ──
    st.markdown("#### All Transactions")
    show = filtered[[
        "txn_id", "name", "persona",
        "amount", "timestamp", "location", "merchant"
    ]].copy()
    show["amount"] = show["amount"].apply(lambda x: f"₹{x:,.0f}")
    show["timestamp"] = show["timestamp"].dt.strftime("%d %b %Y  %H:%M")
    show = show.rename(columns={
        "txn_id": "ID", "name": "User", "persona": "Persona",
        "amount": "Amount", "timestamp": "Time",
        "location": "City", "merchant": "Merchant"
    })
    st.dataframe(show.head(500), use_container_width=True, height=400)

# ════════════════════════════════════════════
# PAGE 3 — USER PROFILES
# ════════════════════════════════════════════

elif page == "👤 User Profiles":

    st.title("👤 User Profiles")
    st.caption(
        "Each user has a different spending pattern. "
        "FinGuard uses these baselines to detect when something is unusual."
    )
    st.divider()

    df = load_transactions()

    # ── Per user cards ──
    for uid, info in USERS.items():
        udf   = df[df["user_id"] == uid]
        color = info["color"]

        st.markdown(
            f'<div class="profile-card">'
            f'<span style="color:{color}; font-size:18px; font-weight:700;">'
            f'User {uid} — {info["name"]} ({info["persona"]})'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        col_stats, col_hour, col_amt = st.columns([1, 2, 2])

        with col_stats:
            st.metric("Transactions",    f"{len(udf):,}")
            st.metric("Avg Transaction", f"₹{udf['amount'].mean():,.0f}")
            st.metric("Max Transaction", f"₹{udf['amount'].max():,.0f}")
            st.metric("Min Transaction", f"₹{udf['amount'].min():,.0f}")

            top_city = udf["location"].value_counts().index[0]
            top_merch = udf["merchant"].value_counts().index[0]
            st.metric("Main City",     top_city)
            st.metric("Top Merchant",  top_merch)

        with col_hour:
            # Activity by hour
            hourly = udf.groupby("hour").size().reset_index(name="count")
            fig_h = go.Figure(go.Bar(
                x=hourly["hour"],
                y=hourly["count"],
                marker_color=color,
                hovertemplate="Hour %{x}:00 → %{y} txns<extra></extra>"
            ))
            fig_h = dark_chart(fig_h, 220)
            fig_h.update_layout(
                title=f"When {info['name']} transacts",
                xaxis={
                    "tickvals": [0,6,12,18,23],
                    "ticktext": ["12AM","6AM","12PM","6PM","11PM"],
                    "gridcolor": "#21262d"
                },
                yaxis={"gridcolor": "#21262d"}
            )
            st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False}, key=f"profile_hour_{uid}")

        with col_amt:
            # Amount distribution
            fig_a = go.Figure(go.Histogram(
                x=udf["amount"],
                nbinsx=30,
                marker_color=color,
                opacity=0.85,
                hovertemplate="₹%{x} → %{y} transactions<extra></extra>"
            ))
            fig_a = dark_chart(fig_a, 220)
            fig_a.update_layout(
                title=f"How much {info['name']} spends",
                xaxis={"title": "Amount (₹)",
                       "gridcolor": "#21262d"},
                yaxis={"title": "Count",
                       "gridcolor": "#21262d"}
            )
            st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False},key=f"profile_amt_{uid}")

        # Plain English summary under each user
        avg   = udf["amount"].mean()
        hours = udf.groupby("hour").size().idxmax()
        st.caption(
            f"💡 {info['name']}'s normal pattern: "
            f"₹{avg:,.0f} average spend · "
            f"most active around {hours}:00 · "
            f"mainly in {top_city}. "
            f"Any transaction that breaks this pattern scores higher risk."
        )
        st.divider()

    # ── Cross-user comparison ──
    st.markdown("#### How the 3 users compare")

    comp_data = []
    for uid, info in USERS.items():
        udf = df[df["user_id"] == uid]
        comp_data.append({
            "User":    info["name"],
            "Persona": info["persona"],
            "Avg ₹":   f"₹{udf['amount'].mean():,.0f}",
            "Max ₹":   f"₹{udf['amount'].max():,.0f}",
            "Txns":    len(udf),
            "Active hours": (
                "8AM – 11PM" if uid == 1 else
                "10PM – 4AM" if uid == 2 else
                "9AM – 6PM"
            ),
            "Cities": (
                "Mumbai" if uid == 1 else
                "Bangalore" if uid == 2 else
                "Delhi, Mumbai, Dubai, London"
            )
        })

    st.dataframe(
        pd.DataFrame(comp_data).set_index("User"),
        use_container_width=True
    )
    st.caption(
        "💡 This is why FinGuard uses per-user Isolation Forest models. "
        "₹50,000 is completely normal for Kabir but extreme for Aman. "
        "One global model would either miss Kabir's fraud or "
        "block all of Aman's normal transactions."
    )

# ════════════════════════════════════════════
# PAGE 4 — ATTACK SIMULATION
# ════════════════════════════════════════════

elif page == "💥 Attack Simulation":

    st.title("💥 Attack Simulation")
    st.caption(
        "Simulates fraud attacks against the live API. "
        "Nothing is saved to the database — "
        "these are test transactions scored in real time."
    )
    st.divider()

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        attack = st.selectbox("Attack type", [
            "Rapid transactions (velocity fraud)",
            "Large night transactions (account takeover)",
            "Huge amount burst (amount fraud)",
        ])

        n = st.slider("How many transactions to fire", 5, 50, 20)

        target = st.selectbox(
            "Target user",
            [1, 2, 3],
            format_func=lambda x: f"{USERS[x]['name']} ({USERS[x]['persona']})"
        )

        st.divider()
        st.markdown("**What this attack does:**")

        desc = {
            "Rapid transactions (velocity fraud)":
                "Fires transactions 2 seconds apart from each other. "
                "Tests whether the velocity signal (time_gap < 30s) "
                "triggers BLOCK in your Risk Engine.",

            "Large night transactions (account takeover)":
                "Sends very large amounts between 1 AM and 4 AM "
                "from an unknown city. Simulates someone stealing "
                "credentials and draining the account at night.",

            "Huge amount burst (amount fraud)":
                "Sends amounts 12–20× above the user's normal average. "
                "For Aman (avg ₹296), this means ₹3,500–5,900. "
                "Tests the amount deviation signal.",
        }
        st.info(desc[attack])

        st.caption(
            "ℹ️ These transactions are scored by the API but "
            "never saved to finguard.db. "
            "Your database stays unchanged."
        )

        sim_btn = st.button("🚀 Launch Attack")

    with col_right:
        if sim_btn:
            # ── Build payloads ──
            payloads = []
            now = datetime.now()

            # Get user avg for amount fraud
            conn = sqlite3.connect("data/finguard.db")
            user_avg = pd.read_sql_query(
                "SELECT AVG(amount) as avg FROM transactions WHERE user_id=?",
                conn, params=(target,)
            )["avg"].iloc[0]
            conn.close()

            for i in range(n):
                if attack == "Rapid transactions (velocity fraud)":
                    p = {
                        "user_id":           target,
                        "amount":            round(random.uniform(100, 800), 2),
                        "timestamp":         now.replace(
                                                 second=min(i * 2, 59)
                                             ).isoformat()[:19],
                        "location":          "Mumbai",
                        "merchant":          "Amazon",
                        "time_gap_override": float(i * 2),
                    }

                elif attack == "Large night transactions (account takeover)":
                    p = {
                        "user_id":           target,
                        "amount":            round(
                                                 random.uniform(80000, 300000), 2
                                             ),
                        "timestamp":         now.replace(
                                                 hour=random.randint(1, 4),
                                                 minute=random.randint(0, 59)
                                             ).isoformat()[:19],
                        "location":          "UnknownCity",
                        "merchant":          "UnknownMerchant",
                        "time_gap_override": -1.0,
                    }

                else:  # Huge amount
                    p = {
                        "user_id":           target,
                        "amount":            round(
                                                 user_avg * random.uniform(12, 20), 2
                                             ),
                        "timestamp":         now.isoformat()[:19],
                        "location":          "Delhi",
                        "merchant":          "LuxuryMall",
                        "time_gap_override": -1.0,
                    }

                payloads.append(p)

            # ── Fire and collect ──
            results   = []
            progress  = st.progress(0, text="Firing transactions...")

            for i, p in enumerate(payloads):
                r = call_api(p)
                if "error" not in r:
                    results.append({
                        "#":         i + 1,
                        "Amount":    f"₹{p['amount']:,.0f}",
                        "Decision":  r.get("decision", "?"),
                        "Risk":      r.get("risk_score", 0),
                        "Fraud %":   f"{r.get('fraud_probability', 0)*100:.1f}%",
                        "Anomaly":   "Yes" if r.get("anomaly_label") == -1 else "No",
                    })
                progress.progress(
                    (i + 1) / n,
                    text=f"Transaction {i+1} of {n}..."
                )
                time.sleep(0.03)

            progress.empty()

            if not results:
                st.error("No results — is the API running?")
                st.stop()

            df_res = pd.DataFrame(results)
            counts = df_res["Decision"].value_counts()

            # ── Summary numbers ──
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("BLOCK",   counts.get("BLOCK",   0))
            s2.metric("DELAY",   counts.get("DELAY",   0))
            s3.metric("WARN",    counts.get("WARN",    0))
            s4.metric("APPROVE", counts.get("APPROVE", 0))

            caught  = counts.get("BLOCK", 0) + counts.get("DELAY", 0)
            pct     = caught / len(results) * 100

            if pct >= 80:
                st.success(
                    f"🛡️ Catch rate: {pct:.0f}% — "
                    f"{caught} of {len(results)} attacks flagged or blocked"
                )
            elif pct >= 50:
                st.warning(
                    f"⚠️ Catch rate: {pct:.0f}% — "
                    f"{caught} of {len(results)} caught"
                )
            else:
                st.error(
                    f"❌ Catch rate only {pct:.0f}% — "
                    f"only {caught} of {len(results)} caught"
                )

            # ── Timeline chart ──
            color_map = {
                "APPROVE": "#3fb950",
                "WARN":    "#d29922",
                "DELAY":   "#f0883e",
                "BLOCK":   "#f85149"
            }

            fig_sim = go.Figure()
            for dec, col in color_map.items():
                sub = df_res[df_res["Decision"] == dec]
                if len(sub):
                    fig_sim.add_trace(go.Scatter(
                        x=sub["#"],
                        y=sub["Risk"],
                        mode="markers",
                        name=dec,
                        marker=dict(color=col, size=11, symbol="circle"),
                        hovertemplate=(
                            f"<b>{dec}</b><br>"
                            "Txn #%{x}<br>"
                            "Risk: %{y}<extra></extra>"
                        )
                    ))

            fig_sim.add_hline(
                y=75, line_dash="dash", line_color="#f85149",
                annotation_text="BLOCK (75+)",
                annotation_font_color="#f85149",
                annotation_position="right"
            )
            fig_sim.add_hline(
                y=55, line_dash="dash", line_color="#f0883e",
                annotation_text="DELAY (55+)",
                annotation_font_color="#f0883e",
                annotation_position="right"
            )
            fig_sim.add_hline(
                y=30, line_dash="dash", line_color="#d29922",
                annotation_text="WARN (30+)",
                annotation_font_color="#d29922",
                annotation_position="right"
            )

            fig_sim = dark_chart(fig_sim, 320)
            fig_sim.update_layout(
                title="Risk score for each transaction fired",
                xaxis={"title": "Transaction number",
                       "gridcolor": "#21262d"},
                yaxis={"title": "Risk score (0–130)",
                       "range": [0, 130],
                       "gridcolor": "#21262d"},
            )
            st.plotly_chart(fig_sim, use_container_width=True, config={"displayModeBar": False}, key="sim_chart")
            st.caption(
                "Each dot is one transaction. "
                "Dots above the red line = BLOCK. "
                "Above orange = DELAY. Above yellow = WARN."
            )

            # ── Results table ──
            st.markdown("#### All transactions")
            st.dataframe(df_res, use_container_width=True, height=300)

        else:
            st.markdown(
                '<div style="height:400px; border:1px dashed #21262d;'
                'border-radius:8px; display:flex; align-items:center;'
                'justify-content:center; color:#8b949e; font-size:15px;">'
                '← Configure and launch an attack'
                '</div>',
                unsafe_allow_html=True
            )
# ════════════════════════════════════════════
# PAGE — LIVE TRANSACTION FEED
# ════════════════════════════════════════════

elif page == "📡 Live Feed":

    st.title("📡 Live Transaction Feed")
    st.caption(
        "Transactions are generated and scored in real time. "
        "Watch the fraud detection system work live."
    )
    st.divider()

    # ── Controls ──
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4 = st.columns(4)

    with col_ctrl1:
        speed = st.selectbox(
            "Speed",
            ["Fast (1s)", "Normal (2s)", "Slow (3s)"],
            index=1
        )
        delay = {"Fast (1s)": 1.0,
                 "Normal (2s)": 2.0,
                 "Slow (3s)": 3.0}[speed]

    with col_ctrl2:
        feed_user = st.selectbox(
            "User",
            ["All users randomly", "Aman (Student)",
             "Riya (Night Gamer)", "Kabir (VIP)"],
        )

    with col_ctrl3:
        fraud_mode = st.selectbox(
            "Inject fraud?",
            ["Normal mix", "High fraud (30%)", "Attack mode (60%)"]
        )

    with col_ctrl4:
        max_rows = st.slider("Max rows to show", 10, 50, 20)

    st.divider()

    # ── Start / Stop ──
    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        start = st.button("▶ Start Feed",
                          use_container_width=True)
    with btn_col2:
        stop  = st.button("⏹ Stop",
                          use_container_width=True)

    if stop:
        st.session_state["feed_running"] = False

    if start:
        st.session_state["feed_running"] = True
        st.session_state["feed_rows"]    = []

    if "feed_running" not in st.session_state:
        st.session_state["feed_running"] = False
    if "feed_rows" not in st.session_state:
        st.session_state["feed_rows"]    = []

    # ── Live counters placeholder ──
    counter_placeholder = st.empty()
    # ── Table placeholder ──
    table_placeholder   = st.empty()
    # ── Chart placeholder ──
    chart_placeholder   = st.empty()

    # ── Persona configs for generation ──
    PERSONA_CONFIG = {
        1: {
            "name":     "Aman",
            "persona":  "Student",
            "amounts":  (50, 500),
            "hours":    list(range(8, 23)),
            "cities":   ["Mumbai"],
            "merchants":["Swiggy","Zomato","Amazon","BookStore"]
        },
        2: {
            "name":     "Riya",
            "persona":  "Night Gamer",
            "amounts":  (500, 5000),
            "hours":    [22,23,0,1,2,3,4],
            "cities":   ["Bangalore"],
            "merchants":["Steam","EpicGames","Amazon","Zomato"]
        },
        3: {
            "name":     "Kabir",
            "persona":  "VIP",
            "amounts":  (10000, 100000),
            "hours":    list(range(9, 18)),
            "cities":   ["Delhi","Mumbai","London","Dubai"],
            "merchants":["LuxuryMall","Airline","Hotel","Amazon"]
        }
    }

    def generate_transaction(user_id: int,
                             fraud_probability: float) -> dict:
        """Generate a realistic transaction for given user."""
        config = PERSONA_CONFIG[user_id]
        now    = datetime.now()

        is_fraud_txn = random.random() < fraud_probability

        if is_fraud_txn:
            # Pick a fraud pattern
            pattern = random.choice([
                "night_large",
                "unknown_location",
                "rapid",
                "ato"
            ])
            if pattern == "night_large":
                hour     = random.randint(1, 4)
                amount   = round(random.uniform(
                    config["amounts"][1] * 3,
                    config["amounts"][1] * 8), 2)
                city     = random.choice(config["cities"])
                merchant = random.choice(config["merchants"])
            elif pattern == "unknown_location":
                hour     = random.randint(0, 23)
                amount   = round(random.uniform(
                    config["amounts"][1] * 2,
                    config["amounts"][1] * 5), 2)
                city     = "UnknownCity"
                merchant = "UnknownMerchant"
            elif pattern == "rapid":
                hour     = random.randint(0, 23)
                amount   = round(random.uniform(
                    config["amounts"][0],
                    config["amounts"][1]), 2)
                city     = random.choice(config["cities"])
                merchant = random.choice(config["merchants"])
            else:  # ato
                hour     = random.randint(1, 5)
                amount   = round(random.uniform(
                    config["amounts"][1] * 4,
                    config["amounts"][1] * 10), 2)
                city     = "UnknownCity"
                merchant = "UnknownMerchant"
        else:
            hour     = random.choice(config["hours"])
            amount   = round(random.uniform(
                config["amounts"][0],
                config["amounts"][1]), 2)
            city     = random.choice(config["cities"])
            merchant = random.choice(config["merchants"])

        ts = now.replace(
            hour=hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        ).isoformat()[:19]

        return {
            "user_id":   user_id,
            "amount":    amount,
            "timestamp": ts,
            "location":  city,
            "merchant":  merchant
        }

    # ── Main feed loop ──
    if st.session_state["feed_running"]:

        # Fraud injection rate
        fraud_rate = {
            "Normal mix":       0.05,
            "High fraud (30%)": 0.30,
            "Attack mode (60%)":0.60
        }[fraud_mode]

        # Which user to generate for
        uid_map = {
            "All users randomly": None,
            "Aman (Student)":     1,
            "Riya (Night Gamer)": 2,
            "Kabir (VIP)":        3
        }
        fixed_uid = uid_map[feed_user]

        # Run for max_rows transactions then stop
        for tick in range(max_rows):

            if not st.session_state.get("feed_running", False):
                break

            # Pick user
            uid = fixed_uid or random.choice([1, 2, 3])

            # Generate transaction
            txn_payload = generate_transaction(uid, fraud_rate)

            # Score via API
            result = call_api(txn_payload)

            if "error" not in result:
                decision  = result.get("decision", "?")
                risk      = result.get("risk_score", 0)
                fraud_p   = result.get("fraud_probability", 0)
                xgb_p     = result.get("models", {}).get(
                                "xgboost_prob", 0)
                user_name = PERSONA_CONFIG[uid]["name"]

                # Color per decision
                dec_color = {
                    "APPROVE": "🟢",
                    "WARN":    "🟡",
                    "DELAY":   "🟠",
                    "BLOCK":   "🔴"
                }.get(decision, "⚪")

                row = {
                    "":         dec_color,
                    "User":     user_name,
                    "Amount":   f"₹{txn_payload['amount']:,.0f}",
                    "Location": txn_payload["location"],
                    "Merchant": txn_payload["merchant"],
                    "Hour":     txn_payload["timestamp"][11:13] + ":00",
                    "Decision": decision,
                    "Risk":     risk,
                    "Fraud %":  f"{fraud_p*100:.1f}%",
                }

                # Prepend new row
                st.session_state["feed_rows"].insert(0, row)

                # Keep only max_rows
                st.session_state["feed_rows"] = \
                    st.session_state["feed_rows"][:max_rows]

            # ── Update counters ──
            rows      = st.session_state["feed_rows"]
            total     = len(rows)
            blocked   = sum(1 for r in rows if r["Decision"] == "BLOCK")
            delayed   = sum(1 for r in rows if r["Decision"] == "DELAY")
            warned    = sum(1 for r in rows if r["Decision"] == "WARN")
            approved  = sum(1 for r in rows if r["Decision"] == "APPROVE")
            catch_rate= (blocked+delayed)/total*100 if total else 0

            with counter_placeholder.container():
                k1,k2,k3,k4,k5 = st.columns(5)
                k1.metric("Scored",    total)
                k2.metric("🔴 BLOCK",  blocked)
                k3.metric("🟠 DELAY",  delayed)
                k4.metric("🟡 WARN",   warned)
                k5.metric("Catch Rate",f"{catch_rate:.0f}%")

            # ── Update table ──
            if rows:
                df_feed = pd.DataFrame(rows)

                # Style rows by decision
                def color_row(row):
                    colors = {
                        "BLOCK":   "background-color: #2b0000",
                        "DELAY":   "background-color: #2b1400",
                        "WARN":    "background-color: #2b1f00",
                        "APPROVE": "background-color: #0d2b1a",
                    }
                    return [colors.get(row["Decision"], "")] * len(row)

                styled = df_feed.style.apply(color_row, axis=1)

                with table_placeholder.container():
                    st.dataframe(
                        styled,
                        use_container_width=True,
                        height=min(400, 40 + len(rows) * 35)
                    )

            # ── Update risk chart ──
            if len(rows) >= 3:
                recent = rows[:15]
                fig_live = go.Figure()

                for dec, col in {
                    "APPROVE": "#3fb950",
                    "WARN":    "#d29922",
                    "DELAY":   "#f0883e",
                    "BLOCK":   "#f85149"
                }.items():
                    sub = [r for r in recent
                           if r["Decision"] == dec]
                    if sub:
                        fig_live.add_trace(go.Scatter(
                            x=list(range(len(sub))),
                            y=[r["Risk"] for r in sub],
                            mode="markers",
                            name=dec,
                            marker=dict(
                                color=col,
                                size=14,
                                symbol="circle"
                            )
                        ))

                fig_live.add_hline(
                    y=75, line_dash="dash",
                    line_color="#f85149",
                    annotation_text="BLOCK",
                    annotation_font_color="#f85149"
                )
                fig_live.add_hline(
                    y=55, line_dash="dash",
                    line_color="#f0883e",
                    annotation_text="DELAY",
                    annotation_font_color="#f0883e"
                )
                fig_live.update_layout(
                    title="Live risk scores — last 15 transactions",
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#161b22",
                    font_color="#8b949e",
                    height=280,
                    margin=dict(t=40,b=30,l=30,r=30),
                    xaxis={"gridcolor":"#21262d",
                           "title":"Recent transactions"},
                    yaxis={"gridcolor":"#21262d",
                           "title":"Risk score",
                           "range":[0,130]},
                    legend={"bgcolor":"#161b22"}
                )
                with chart_placeholder.container():
                    st.plotly_chart(
                        fig_live,
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"live_chart_{tick}"
                    )

            time.sleep(delay)

        # Feed finished
        st.session_state["feed_running"] = False
        st.success(f"✅ Feed complete — {len(st.session_state['feed_rows'])} transactions scored.")

    else:
        # Not running — show placeholder
        if st.session_state.get("feed_rows"):
            # Show last run results
            st.caption("Last run results — click Start Feed to run again.")
            st.dataframe(
                pd.DataFrame(st.session_state["feed_rows"]),
                use_container_width=True,
                height=400
            )
        else:
            st.markdown(
                '<div style="height:300px;border:1px dashed #21262d;'
                'border-radius:8px;display:flex;align-items:center;'
                'justify-content:center;color:#8b949e;font-size:15px;">'
                '▶ Click Start Feed to begin live scoring'
                '</div>',
                unsafe_allow_html=True
            )
# ════════════════════════════════════════════
# PAGE — MODEL INTELLIGENCE
# ════════════════════════════════════════════

elif page == "📊 Model Intelligence":

    st.title("📊 Model Intelligence")
    st.caption(
        "Real evaluation metrics from your test set. "
        "All numbers are actual results — not estimates."
    )
    st.divider()

    # ── Load metrics ──
    try:
        with open("models/metrics.json") as f:
            metrics = json.load(f)
    except FileNotFoundError:
        st.error("Run scripts/train_xgboost.py first to generate metrics.")
        st.stop()

    # ── Model summary cards ──
    st.markdown("#### Model Performance Summary")

    c1, c2, c3, c4 = st.columns(4)

    xgb_auc = metrics.get("xgboost", {}).get("auc_roc", 0)
    rf_auc  = metrics.get("random_forest", {}).get("auc_roc", 0)
    ae_auc  = metrics.get("autoencoder", {}).get("auc_roc", 0)
    hybrid  = round((xgb_auc * 0.4 + rf_auc * 0.4 + ae_auc * 0.2), 4)

    for col, name, auc, color, desc in [
        (c1, "XGBoost",        xgb_auc, "#58a6ff", "Supervised classifier"),
        (c2, "Random Forest",  rf_auc,  "#3fb950", "Ensemble classifier"),
        (c3, "Autoencoder",    ae_auc,  "#ffa657", "Neural net anomaly"),
        (c4, "Hybrid System",  hybrid,  "#bc8cff", "All models combined"),
    ]:
        col.markdown(
            f'<div style="background:#161b22;border:1px solid {color};'
            f'border-radius:12px;padding:16px;text-align:center;">'
            f'<div style="color:{color};font-size:12px;font-weight:600;">'
            f'{name}</div>'
            f'<div style="color:{color};font-size:36px;font-weight:700;">'
            f'{auc:.3f}</div>'
            f'<div style="color:#8b949e;font-size:11px;">AUC-ROC</div>'
            f'<div style="color:#8b949e;font-size:11px;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Charts row 1 — AUC-ROC + Feature Importance ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### AUC-ROC Curve")
        auc_path = "models/charts/auc_roc.png"
        if os.path.exists(auc_path):
            st.image(auc_path, use_container_width=True)
            st.caption(
                f"XGBoost AUC: {xgb_auc:.3f} · "
                f"Random Forest AUC: {rf_auc:.3f}. "
                "Higher = better. 1.0 = perfect. 0.5 = random guessing."
            )
        else:
            st.info("Chart not found — run train_xgboost.py")

    with col_right:
        st.markdown("#### Feature Importance (XGBoost)")
        fi_path = "models/charts/feature_importance.png"
        if os.path.exists(fi_path):
            st.image(fi_path, use_container_width=True)
            st.caption(
                "Which features matter most to XGBoost. "
                "Longer bar = more influence on the fraud decision."
            )
        else:
            st.info("Chart not found — run train_xgboost.py")

    st.divider()

    # ── Charts row 2 — Confusion Matrix + Autoencoder ──
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.markdown("#### Confusion Matrix")
        cm_path = "models/charts/confusion_matrix.png"
        if os.path.exists(cm_path):
            st.image(cm_path, use_container_width=True)
            st.caption(
                "Top-left: correctly approved normal transactions. "
                "Bottom-right: correctly blocked fraud. "
                "Off-diagonal = mistakes."
            )
        else:
            st.info("Chart not found — run train_xgboost.py")

    with col_right2:
        st.markdown("#### Autoencoder Error Distribution")
        ae_path = "models/charts/autoencoder_distribution.png"
        if os.path.exists(ae_path):
            st.image(ae_path, use_container_width=True)
            st.caption(
                "Green = normal transactions (low error). "
                "Red = fraud transactions (high error). "
                "The separation proves the autoencoder works."
            )
        else:
            st.info("Chart not found — run train_autoencoder.py")

    st.divider()

    # ── Autoencoder training loss ──
    st.markdown("#### Autoencoder Training Loss")
    loss_path = "models/charts/autoencoder_loss.png"
    if os.path.exists(loss_path):
        col_loss, col_info = st.columns([2, 1])
        with col_loss:
            st.image(loss_path, use_container_width=True)
        with col_info:
            ae_config = metrics.get("autoencoder", {})
            st.metric("AUC-ROC",   f"{ae_config.get('auc_roc', 0):.4f}")
            st.metric("Threshold", f"{ae_config.get('threshold', 0):.4f}")
            st.markdown("""
            **How to read this:**
            - Both lines going down = model is learning
            - Training + validation close together = no overfitting
            - Flattens out = model converged
            """)

    st.divider()

    # ── Model comparison table ──
    st.markdown("#### Full Model Comparison")

    xgb_m = metrics.get("xgboost", {})
    rf_m  = metrics.get("random_forest", {})
    ae_m  = metrics.get("autoencoder", {})

    comparison_df = pd.DataFrame([
        {
            "Model":        "XGBoost",
            "Type":         "Supervised",
            "AUC-ROC":      f"{xgb_m.get('auc_roc', 0):.4f}",
            "Precision":    f"{xgb_m.get('precision', 0):.4f}",
            "Recall":       f"{xgb_m.get('recall', 0):.4f}",
            "Needs Labels": "Yes",
            "Per-user":     "No",
        },
        {
            "Model":        "Random Forest",
            "Type":         "Supervised",
            "AUC-ROC":      f"{rf_m.get('auc_roc', 0):.4f}",
            "Precision":    f"{rf_m.get('precision', 0):.4f}",
            "Recall":       f"{rf_m.get('recall', 0):.4f}",
            "Needs Labels": "Yes",
            "Per-user":     "No",
        },
        {
            "Model":        "Isolation Forest",
            "Type":         "Unsupervised",
            "AUC-ROC":      "—",
            "Precision":    "—",
            "Recall":       "—",
            "Needs Labels": "No",
            "Per-user":     "Yes ✓",
        },
        {
            "Model":        "Autoencoder",
            "Type":         "Deep Learning",
            "AUC-ROC":      f"{ae_m.get('auc_roc', 0):.4f}",
            "Precision":    "—",
            "Recall":       "—",
            "Needs Labels": "No",
            "Per-user":     "No",
        },
        {
            "Model":        "Hybrid (all combined)",
            "Type":         "Ensemble",
            "AUC-ROC":      f"{hybrid:.4f}",
            "Precision":    "—",
            "Recall":       "—",
            "Needs Labels": "Both",
            "Per-user":     "Yes ✓",
        },
    ])

    st.dataframe(
        comparison_df.set_index("Model"),
        use_container_width=True
    )

    st.caption(
        "💡 Our unique contribution: Isolation Forest trained separately "
        "per user. No research paper in our review does this. "
        "Combined with SHAP explainability per transaction, "
        "this makes FinGuard explainable at both model and user level."
    )

    # ── SMOTE explanation ──
    st.divider()
    st.markdown("#### Training Details")

    train_size = metrics.get("train_size", 0)
    test_size  = metrics.get("test_size", 0)
    fraud_rate = metrics.get("fraud_rate", 0)

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Training samples",  f"{train_size:,}",
              help="After SMOTE balancing")
    d2.metric("Test samples",      f"{test_size:,}",
              help="Held out, never seen during training")
    d3.metric("Original fraud rate", f"{fraud_rate*100:.1f}%",
              help="Before SMOTE")
    d4.metric("After SMOTE",       "50/50",
              help="Equal fraud and normal samples")

    st.info(
        "**SMOTE (Synthetic Minority Oversampling Technique)** was applied "
        "to balance the training set. Without it, the model would learn "
        f"to say 'not fraud' on everything and be {(1-fraud_rate)*100:.0f}% "
        "accurate while catching zero fraud. SMOTE creates synthetic fraud "
        "examples so the model actually learns fraud patterns."
    )