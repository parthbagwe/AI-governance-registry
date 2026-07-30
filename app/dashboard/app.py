import requests
import streamlit as st
import pandas as pd
import plotly.express as px

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="AI Model Watchtower", layout="wide", page_icon="🏦")

# -----------------------------------------------------------------
# Plain-English translations of the technical stage names.
# The real value stored in the database is still "pilot"/"review"/etc —
# we only change how it's DISPLAYED, never what's sent to the API.
# -----------------------------------------------------------------
STAGE_DISPLAY = {
    "pilot": ("🧪 Testing", "#f59e0b", "Being tried out. Not yet trusted with real decisions."),
    "review": ("🔍 Under Review", "#3b82f6", "Being checked by the approval team before it can go live."),
    "production": ("✅ Live & Active", "#22c55e", "Actively making real decisions right now."),
    "deprecated": ("⛔ Retired", "#6b7280", "Switched off. No longer used."),
}

SCORE_LABELS = {
    "efficiency_score": ("⚡ Efficiency", "Does it save time or work compared to doing this manually?"),
    "adoption_score": ("👥 Adoption", "Are the actual teams/staff using it and trusting it?"),
    "input_quality_score": ("📊 Data Quality", "Is the data feeding it clean and reliable?"),
    "cost_reduction_score": ("💰 Cost Savings", "Is it saving the bank money?"),
    "revenue_impact_score": ("📈 Revenue Impact", "Is it helping bring in more business?"),
}


def score_traffic_light(score):
    """Convert a 0-10 score into a plain traffic-light judgment."""
    if score is None:
        return "⚪", "Not scored yet"
    if score >= 7:
        return "🟢", "Good"
    if score >= 4:
        return "🟡", "Needs attention"
    return "🔴", "Poor"


@st.cache_data(ttl=5)
def get_models():
    return requests.get(f"{API_BASE}/models").json()


def get_history(model_id):
    return requests.get(f"{API_BASE}/models/{model_id}/history").json()


def get_metrics(model_id, metric_name=None):
    params = {"metric_name": metric_name} if metric_name else {}
    return requests.get(f"{API_BASE}/models/{model_id}/metrics", params=params).json()


def get_lineage(model_id):
    return requests.get(f"{API_BASE}/models/{model_id}/lineage").json()


# ===================================================================
# HEADER + PLAIN-ENGLISH EXPLAINER
# ===================================================================
st.title("🏦 AI Model Watchtower")
st.markdown(
    "This tool keeps track of every AI model the bank uses — what it's for, "
    "whether it's safe to trust with real decisions, and who approved it."
)

with st.expander("ℹ️  What am I looking at? (click to expand)", expanded=False):
    st.markdown("""
    Think of this like a **quality-control checklist for AI models**, similar to how
    a bank branch might track which staff are fully trained versus still in onboarding.

    - **🧪 Testing** — the model is new and being tried out quietly, not yet trusted.
    - **🔍 Under Review** — a human team is checking it before letting it go live.
    - **✅ Live & Active** — it's approved and currently making real decisions.
    - **⛔ Retired** — it's been switched off.

    A model can **only** become "✅ Live & Active" if it scores well across five checks
    (efficiency, adoption, data quality, cost savings, revenue impact). If it doesn't,
    the system **automatically blocks it** — no person can override that by clicking a button.

    There's also an automatic "health monitor" that watches live models. If a model's
    real-world data starts looking very different from what it was trained on, it gets
    **automatically pulled back for re-review** — the same way a bank might re-audit a
    process if conditions on the ground changed.
    """)

try:
    models = get_models()
except requests.exceptions.ConnectionError:
    st.error(
        "🚫 Can't reach the backend server. Make sure the API is running "
        "(`python -m uvicorn app.main:app --reload`) in a separate terminal, then refresh this page."
    )
    st.stop()

if not models:
    st.warning("No models found yet. Run `python seed.py` in your terminal first, then refresh.")
    st.stop()

st.divider()

# ===================================================================
# OVERVIEW CARDS — one glance, no jargon
# ===================================================================
st.subheader("📋 All AI Models at a Glance")

cols = st.columns(len(models))
for col, m in zip(cols, models):
    label, color, desc = STAGE_DISPLAY.get(m["stage"], (m["stage"], "#888", ""))
    with col:
        st.markdown(
            f"""
            <div style="border:1px solid {color}55; border-radius:12px; padding:16px; background-color:{color}11;">
                <div style="font-size:15px; font-weight:700;">{m['name']}</div>
                <div style="font-size:13px; color:#999; margin-bottom:8px;">{m['use_case']}</div>
                <div style="display:inline-block; background-color:{color}33; padding:4px 10px;
                            border-radius:6px; font-weight:600; font-size:13px;">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ===================================================================
# MODEL SELECTOR
# ===================================================================
st.subheader("🔎 Look at One Model in Detail")

model_names = {f"{m['name']}": m for m in models}
selected_label = st.selectbox("Choose a model", list(model_names.keys()))
selected = model_names[selected_label]
model_id = selected["id"]
stage_label, stage_color, stage_desc = STAGE_DISPLAY.get(selected["stage"], (selected["stage"], "#888", ""))

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"### {selected['name']}")
    st.write(f"**What it's for:** {selected['use_case']}")
    st.write(f"**Who owns it:** {selected['owner']}")
    st.markdown(
        f"**Current status:** <span style='background-color:{stage_color}33; "
        f"padding:5px 12px; border-radius:6px; font-weight:600'>{stage_label}</span>",
        unsafe_allow_html=True,
    )
    st.caption(stage_desc)

with col2:
    gscore = selected["governance_score"]
    emoji, verdict = score_traffic_light(gscore)
    st.metric("Overall Health Score", f"{gscore}/10" if gscore is not None else "Not yet scored")
    st.markdown(f"### {emoji} {verdict}")

st.write("")
st.write("**The Five Checks**")
st.caption("A model needs to pass all five, with an average of 7/10 or higher, before it can go live.")

score_cols = st.columns(5)
for col, (field, (label, tooltip)) in zip(score_cols, SCORE_LABELS.items()):
    val = selected[field]
    emoji, verdict = score_traffic_light(val)
    with col:
        st.markdown(f"**{label}**")
        st.markdown(f"## {emoji}")
        st.caption(f"{val}/10" if val is not None else "Not scored")
        st.caption(tooltip)

st.divider()

# ===================================================================
# PERFORMANCE CHART — plain-language framing
# ===================================================================
st.subheader("📈 Is This Model Still Working Well?")
st.caption("This chart shows how accurate/reliable the model has been over time. "
           "A sudden drop is a warning sign — it may mean the model needs re-checking.")

metrics = get_metrics(model_id)
if metrics:
    mdf = pd.DataFrame(metrics)
    mdf["recorded_at"] = pd.to_datetime(mdf["recorded_at"])
    available_metrics = mdf["metric_name"].unique().tolist()

    default_pick = [m for m in available_metrics if "accuracy" in m] or available_metrics[:1]
    chosen_metrics = st.multiselect("Show me:", available_metrics, default=default_pick)

    if chosen_metrics:
        plot_df = mdf[mdf["metric_name"].isin(chosen_metrics)]
        fig = px.line(
            plot_df, x="recorded_at", y="metric_value", color="metric_name",
            markers=True, labels={"recorded_at": "Date", "metric_value": "Score", "metric_name": "Measurement"},
        )
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No performance data recorded for this model yet.")

st.divider()

# ===================================================================
# GOVERNANCE ACTIONS — guided, not free-form
# ===================================================================
st.subheader("⚙️ Change This Model's Status")

action_options = {
    "🔍 Send for Review": "review",
    "✅ Approve for Live Use": "production",
    "⛔ Retire It": "deprecated",
    "🧪 Send Back to Testing": "pilot",
}

chosen_action_label = st.radio("What would you like to do?", list(action_options.keys()), horizontal=True)
target_stage = action_options[chosen_action_label]

# Pre-emptive plain-English warning BEFORE they click, so it's not a surprise
if target_stage == "production" and (gscore is None or gscore < 7):
    st.warning(
        f"⚠️ Heads up: this model's health score is "
        f"{'not yet available' if gscore is None else f'{gscore}/10'}, which is below the "
        f"7/10 needed to go live. The system will likely block this request — that's intentional, "
        f"it's protecting against pushing an unready model into real use."
    )

approver = st.text_input("Your name (for the record)", value="")
confirm = st.checkbox("I understand this action will be logged permanently.")
submit = st.button("Submit Request", type="primary", disabled=not approver or not confirm)

if submit:
    resp = requests.post(
        f"{API_BASE}/models/{model_id}/approve",
        json={"to_stage": target_stage, "approved_by": approver, "comment": "Submitted via dashboard"},
    )
    if resp.status_code == 200:
        new_label = STAGE_DISPLAY.get(resp.json()["stage"], (resp.json()["stage"],))[0]
        st.success(f"✅ Done! This model's status is now: {new_label}")
        st.cache_data.clear()
        st.balloons()
    else:
        st.error(f"🚫 Request blocked. Reason: {resp.json()['detail']}")

st.divider()

# ===================================================================
# HISTORY + LINEAGE — plain framing
# ===================================================================
hist_col, lineage_col = st.columns(2)

with hist_col:
    st.subheader("🕒 Full History")
    st.caption("Every change ever made to this model, and who made it.")
    history = get_history(model_id)
    for event in reversed(history):
        from_label = STAGE_DISPLAY.get(event["from_stage"], ("New model", "", ""))[0] if event["from_stage"] else "Newly registered"
        to_label = STAGE_DISPLAY.get(event["to_stage"], (event["to_stage"], "", ""))[0]
        st.write(f"**{event['created_at'][:10]}** — {from_label} → {to_label}")
        st.caption(f"By: {event['approved_by']}" + (f" — \"{event['comment']}\"" if event["comment"] else ""))

with lineage_col:
    st.subheader("🔗 What Data Feeds This Model")
    st.caption("If any of this data changes or breaks, this model may need re-checking.")
    lineage = get_lineage(model_id)
    if lineage:
        for l in lineage:
            st.write(f"**📁 {l['source_table']}**")
            st.caption("Uses: " + ", ".join(l["features_used"]))
    else:
        st.info("No data sources recorded for this model.")