import requests
import streamlit as st
import pandas as pd
import plotly.express as px

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="AI Governance Registry", layout="wide")
st.title("🏦 AI Model Governance Registry")
st.caption("Tracks ML/LLM/SLM models through pilot → review → production → deprecated, "
           "with a five-dimension governance scorecard and full audit trail.")

STAGE_COLORS = {
    "pilot": "#f59e0b", "review": "#3b82f6",
    "production": "#22c55e", "deprecated": "#6b7280",
}


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


models = get_models()

if not models:
    st.warning("No models found. Run `python seed.py` first.")
    st.stop()

st.subheader("Model Registry")

df = pd.DataFrame(models)
display_df = df[["name", "version", "model_type", "stage", "governance_score", "owner"]].copy()
st.dataframe(
    display_df.style.apply(
        lambda row: [f"background-color: {STAGE_COLORS.get(row['stage'], '#fff')}22"] * len(row),
        axis=1,
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

model_names = {f"{m['name']} ({m['version']})": m for m in models}
selected_label = st.selectbox("Select a model to inspect", list(model_names.keys()))
selected = model_names[selected_label]
model_id = selected["id"]

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"📋 {selected['name']}")
    st.write(f"**Use case:** {selected['use_case']}")
    st.write(f"**Owner:** {selected['owner']}  |  **Type:** {selected['model_type']}")

    stage_color = STAGE_COLORS.get(selected["stage"], "#888")
    st.markdown(
        f"**Current stage:** <span style='background-color:{stage_color}33; "
        f"padding:4px 10px; border-radius:6px; font-weight:600'>{selected['stage'].upper()}</span>",
        unsafe_allow_html=True,
    )

with col2:
    st.metric("Governance Score", selected["governance_score"] or "—", help="Average of 5 scorecard dimensions")

st.write("**Governance Scorecard**")
score_fields = {
    "Efficiency": selected["efficiency_score"],
    "Adoption": selected["adoption_score"],
    "Input Quality": selected["input_quality_score"],
    "Cost Reduction": selected["cost_reduction_score"],
    "Revenue Impact": selected["revenue_impact_score"],
}
score_cols = st.columns(5)
for col, (label, val) in zip(score_cols, score_fields.items()):
    col.metric(label, val if val is not None else "—")

st.divider()

st.subheader("📈 Performance Metrics Over Time")

metrics = get_metrics(model_id)
if metrics:
    mdf = pd.DataFrame(metrics)
    mdf["recorded_at"] = pd.to_datetime(mdf["recorded_at"])

    available_metrics = mdf["metric_name"].unique().tolist()
    chosen_metrics = st.multiselect(
        "Metrics to plot", available_metrics,
        default=[m for m in available_metrics if m in ("accuracy", "real_accuracy")] or available_metrics[:1],
    )
    if chosen_metrics:
        plot_df = mdf[mdf["metric_name"].isin(chosen_metrics)]
        fig = px.line(
            plot_df, x="recorded_at", y="metric_value", color="metric_name",
            markers=True, title=f"{selected['name']} — metric history",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No metrics logged yet for this model.")

st.divider()

st.subheader("⚙️ Governance Actions")

action_col1, action_col2, action_col3 = st.columns([2, 2, 1])
with action_col1:
    target_stage = st.selectbox("Move to stage", ["review", "production", "deprecated", "pilot"])
with action_col2:
    approver = st.text_input("Approved by", value="dashboard-user")
with action_col3:
    st.write("")
    st.write("")
    submit = st.button("Submit transition", type="primary")

if submit:
    resp = requests.post(
        f"{API_BASE}/models/{model_id}/approve",
        json={"to_stage": target_stage, "approved_by": approver, "comment": "Submitted via dashboard"},
    )
    if resp.status_code == 200:
        st.success(f"✅ Transition succeeded: model is now '{resp.json()['stage']}'")
        st.cache_data.clear()
    else:
        st.error(f"🚫 Transition blocked (HTTP {resp.status_code}): {resp.json()['detail']}")

st.divider()

hist_col, lineage_col = st.columns(2)

with hist_col:
    st.subheader("🕒 Audit Trail")
    history = get_history(model_id)
    for event in history:
        st.write(
            f"**{event['created_at'][:19]}** — "
            f"`{event['from_stage'] or 'new'}` → `{event['to_stage']}` "
            f"by *{event['approved_by']}*"
        )
        if event["comment"]:
            st.caption(event["comment"])

with lineage_col:
    st.subheader("🔗 Data Lineage")
    lineage = get_lineage(model_id)
    if lineage:
        for l in lineage:
            st.write(f"**{l['source_table']}**")
            st.caption(", ".join(l["features_used"]))
    else:
        st.info("No lineage recorded for this model.")