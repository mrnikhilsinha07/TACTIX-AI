from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"

st.set_page_config(page_title="TACTIX AI | Transition Intelligence", page_icon="⚽", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: rgba(120,120,120,.08); padding: 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("⚽ TACTIX AI")
st.subheader("Transition Intelligence | Possession-loss analysis")
st.caption("Exploratory analysis of StatsBomb Open Data. Candidate turnover indicators are proxies, not verified ground truth.")

summary_path = REPORTS / "validation_summary.json"
transitions_path = REPORTS / "transition_candidates.csv"
matches_path = REPORTS / "sample_matches.csv"
coverage_path = REPORTS / "event_type_coverage.csv"

missing = [p.name for p in [summary_path, transitions_path, matches_path, coverage_path] if not p.exists()]
if missing:
    st.error("Required validation reports are missing: " + ", ".join(missing))
    st.info("Run the validation script first: .\\.venv\\Scripts\\python.exe src\\validate_statsbomb.py")
    st.stop()

summary = json.loads(summary_path.read_text(encoding="utf-8"))
df = pd.read_csv(transitions_path)
matches = pd.read_csv(matches_path)
coverage = pd.read_csv(coverage_path)

for col in ["team_losing_possession", "opponent_next_possession", "loss_indicator", "loss_event_type", "opponent_first_event"]:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown").astype(str)

st.markdown(f"**Dataset:** {summary.get('competition', 'Unknown')} — {summary.get('season', 'Unknown')}  ·  **Matches loaded:** {summary.get('matches_with_events_loaded', 0)}")

with st.sidebar:
    st.header("Filters")
    teams = sorted(set(df["team_losing_possession"].dropna().astype(str)))
    selected_teams = st.multiselect("Team losing possession", teams, default=teams)
    reasons = sorted(set(df["loss_indicator"].dropna().astype(str)))
    selected_reasons = st.multiselect("Loss indicator", reasons, default=reasons)
    match_ids = sorted(df["match_id"].dropna().astype(int).unique().tolist())
    selected_matches = st.multiselect("Match IDs", match_ids, default=match_ids)

filtered = df[
    df["team_losing_possession"].isin(selected_teams)
    & df["loss_indicator"].isin(selected_reasons)
    & df["match_id"].isin(selected_matches)
].copy()

total = len(filtered)
with_shot = int(filtered["opponent_possession_contains_shot"].fillna(False).astype(bool).sum()) if total else 0
shot_rate = (100 * with_shot / total) if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidate transition records", f"{total:,}")
c2.metric("Next possession contains shot", f"{with_shot:,}")
c3.metric("Share with subsequent shot", f"{shot_rate:.1f}%")
c4.metric("Matches in dataset", f"{filtered['match_id'].nunique() if total else 0}")

st.warning("Interpretation guardrail: this is a small exploratory sample. A shot in the next possession does not prove that the loss caused it. Do not interpret these numbers as causal effects or a definitive pressing score.")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Where possession was lost", "Transition outcomes", "Data quality"])

with tab1:
    left, right = st.columns(2)
    with left:
        if total:
            reason_counts = filtered["loss_indicator"].value_counts().rename_axis("Indicator").reset_index(name="Records")
            fig = px.bar(reason_counts, x="Indicator", y="Records", title="Candidate loss indicators", text="Records")
            fig.update_layout(xaxis_title="", yaxis_title="Records")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No records match the selected filters.")
    with right:
        if total:
            team_counts = filtered["team_losing_possession"].value_counts().head(15).rename_axis("Team").reset_index(name="Records")
            fig = px.bar(team_counts.sort_values("Records"), x="Records", y="Team", orientation="h", title="Teams with most candidate indicators")
            st.plotly_chart(fig, width="stretch")
    st.subheader("Sample matches")
    st.dataframe(matches, width="stretch", hide_index=True)

with tab2:
    loc = filtered.dropna(subset=["loss_x", "loss_y"]).copy()
    if not loc.empty:
        fig = px.scatter(
            loc, x="loss_x", y="loss_y", color="loss_indicator",
            hover_data=["team_losing_possession", "match_id", "minute", "second"],
            title="Locations of candidate possession-loss events",
            labels={"loss_x": "Pitch length coordinate", "loss_y": "Pitch width coordinate"}
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(xaxis_range=[0, 120], yaxis_range=[80, 0])
        st.plotly_chart(fig, width="stretch")
        st.caption("Coordinates are plotted in the source event coordinate system; this is not a full pitch drawing.")
    else:
        st.info("No location coordinates available for the selected records.")

with tab3:
    if total:
        outcomes = filtered.groupby("loss_indicator", dropna=False).agg(
            candidate_records=("match_id", "size"),
            next_possession_with_shot=("opponent_possession_contains_shot", lambda s: s.fillna(False).astype(bool).sum()),
        ).reset_index()
        outcomes["share_with_shot_pct"] = (100 * outcomes["next_possession_with_shot"] / outcomes["candidate_records"]).round(1)
        fig = px.bar(outcomes, x="loss_indicator", y="share_with_shot_pct", hover_data=["candidate_records", "next_possession_with_shot"], title="Share of candidate records whose next possession contains a shot", text="share_with_shot_pct")
        fig.update_layout(xaxis_title="Candidate indicator", yaxis_title="Records (%)")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(outcomes, width="stretch", hide_index=True)
    else:
        st.info("No records match the selected filters.")

with tab4:
    st.subheader("Validation summary")
    st.json(summary)
    st.subheader("Event type coverage")
    st.dataframe(coverage, width="stretch", hide_index=True)
    st.subheader("Candidate transition records")
    st.dataframe(filtered.head(500), width="stretch", hide_index=True)
    st.download_button(
        "Download filtered transition records (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="tactix_filtered_transition_records.csv",
        mime="text/csv",
    )

st.divider()
st.caption("Data source: StatsBomb Open Data. Credit StatsBomb and comply with the repository's current attribution and usage requirements when sharing results.")
