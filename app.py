from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"

st.set_page_config(
    page_title="TACTIX AI | Transition Intelligence",
    page_icon="⚽",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: rgba(120,120,120,.08);
        padding: 14px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ TACTIX AI")
st.subheader("Transition Intelligence | Possession-loss analysis")
st.caption(
    "Exploratory analysis of StatsBomb Open Data. Candidate turnover indicators "
    "are proxies, not verified ground truth."
)

# Keep report requirements explicit so a broken or outdated report fails clearly.
REQUIRED_COLUMNS = {
    "transition_candidates.csv": {
        "match_id",
        "team_losing_possession",
        "opponent_next_possession",
        "loss_indicator",
        "loss_event_type",
        "loss_x",
        "loss_y",
        "minute",
        "second",
        "opponent_possession_contains_shot",
    },
    "sample_matches.csv": {"match_id", "home_team", "away_team"},
    "event_type_coverage.csv": {"event_type", "count"},
}

summary_path = REPORTS / "validation_summary.json"
transitions_path = REPORTS / "transition_candidates.csv"
matches_path = REPORTS / "sample_matches.csv"
coverage_path = REPORTS / "event_type_coverage.csv"
report_paths = {
    "validation_summary.json": summary_path,
    "transition_candidates.csv": transitions_path,
    "sample_matches.csv": matches_path,
    "event_type_coverage.csv": coverage_path,
}

missing_files = [name for name, path in report_paths.items() if not path.is_file()]
if missing_files:
    st.error("Required validation reports are missing: " + ", ".join(missing_files))
    st.info(
        "Run the validation script first: "
        r".\.venv\Scripts\python.exe src\validate_statsbomb.py"
    )
    st.stop()

try:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("validation_summary.json must contain a JSON object.")

    df = pd.read_csv(transitions_path)
    matches = pd.read_csv(matches_path)
    coverage = pd.read_csv(coverage_path)
except (OSError, UnicodeDecodeError, json.JSONDecodeError, pd.errors.ParserError, ValueError) as exc:
    st.error(f"Could not read the validation reports: {exc}")
    st.info("Check the report files and rerun src/validate_statsbomb.py if necessary.")
    st.stop()

schema_errors = []
for filename, required in REQUIRED_COLUMNS.items():
    frame = {
        "transition_candidates.csv": df,
        "sample_matches.csv": matches,
        "event_type_coverage.csv": coverage,
    }[filename]
    absent = sorted(required - set(frame.columns))
    if absent:
        schema_errors.append(f"{filename}: missing columns: {', '.join(absent)}")

if schema_errors:
    st.error("The validation reports do not match the expected schema.")
    for error in schema_errors:
        st.write(f"- {error}")
    st.info("Regenerate the reports using src/validate_statsbomb.py.")
    st.stop()

# Normalize text columns for display and filtering.
for col in [
    "team_losing_possession",
    "opponent_next_possession",
    "loss_indicator",
    "loss_event_type",
]:
    df[col] = df[col].fillna("Unknown").astype(str)

# Convert types defensively. Invalid IDs/coordinates become missing rather than crashing.
df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce").astype("Int64")
df["loss_x"] = pd.to_numeric(df["loss_x"], errors="coerce")
df["loss_y"] = pd.to_numeric(df["loss_y"], errors="coerce")
df["minute"] = pd.to_numeric(df["minute"], errors="coerce")
df["second"] = pd.to_numeric(df["second"], errors="coerce")

def parse_bool(value):
    """Parse actual booleans and common CSV boolean representations safely."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n", ""}:
            return False
    return False

df["opponent_possession_contains_shot"] = df[
    "opponent_possession_contains_shot"
].map(parse_bool)

# Summary and data-quality signals.
st.markdown(
    f"**Dataset:** {summary.get('competition', 'Unknown')} — "
    f"{summary.get('season', 'Unknown')}  ·  "
    f"**Matches loaded:** {summary.get('matches_with_events_loaded', 0)}"
)

quality_warnings = []
if df["match_id"].isna().any():
    quality_warnings.append("Some candidate records have invalid or missing match IDs.")
if df[["loss_x", "loss_y"]].isna().any(axis=None):
    quality_warnings.append("Some candidate records have missing or invalid location coordinates.")
if df["team_losing_possession"].eq("Unknown").any():
    quality_warnings.append("Some candidate records have an unknown team.")
if summary.get("download_errors"):
    quality_warnings.append(
        f"{len(summary['download_errors'])} match event file(s) could not be downloaded."
    )

with st.sidebar:
    st.header("Filters")
    all_teams = sorted(df["team_losing_possession"].dropna().unique().tolist())
    all_reasons = sorted(df["loss_indicator"].dropna().unique().tolist())
    all_match_ids = sorted(df["match_id"].dropna().astype(int).unique().tolist())

    selected_teams = st.multiselect("Team losing possession", all_teams, default=all_teams)
    selected_reasons = st.multiselect("Loss indicator", all_reasons, default=all_reasons)
    selected_matches = st.multiselect("Match IDs", all_match_ids, default=all_match_ids)

filtered = df[
    df["team_losing_possession"].isin(selected_teams)
    & df["loss_indicator"].isin(selected_reasons)
    & df["match_id"].isin(selected_matches)
].copy()

total = len(filtered)
with_shot = int(filtered["opponent_possession_contains_shot"].sum()) if total else 0
shot_rate = (100 * with_shot / total) if total else 0.0
match_count = int(filtered["match_id"].nunique()) if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidate transition records", f"{total:,}")
c2.metric("Next possession contains shot", f"{with_shot:,}")
c3.metric("Share with subsequent shot", f"{shot_rate:.1f}%")
c4.metric("Matches in filtered data", f"{match_count:,}")

st.warning(
    "Interpretation guardrail: this is exploratory analysis. A shot in the next "
    "possession does not prove that the candidate loss caused it. These indicators "
    "are not confirmed turnovers or a definitive pressing score."
)

if quality_warnings:
    with st.expander(f"Data-quality warnings ({len(quality_warnings)})", expanded=False):
        for warning in quality_warnings:
            st.warning(warning)
else:
    st.caption("Basic report checks passed. This is not a full independent validation of the source data.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Overview", "Where possession was lost", "Transition outcomes", "Match analysis", "Data quality", "Team comparison"]
)

with tab1:
    left, right = st.columns(2)
    with left:
        if total:
            reason_counts = (
                filtered["loss_indicator"]
                .value_counts()
                .rename_axis("Indicator")
                .reset_index(name="Records")
            )
            fig = px.bar(
                reason_counts,
                x="Indicator",
                y="Records",
                title="Candidate loss indicators",
                text="Records",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Records")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No records match the selected filters.")

    with right:
        if total:
            team_counts = (
                filtered["team_losing_possession"]
                .value_counts()
                .head(15)
                .sort_values()
                .rename_axis("Team")
                .reset_index(name="Records")
            )
            fig = px.bar(
                team_counts,
                x="Records",
                y="Team",
                orientation="h",
                title="Teams with most candidate indicators",
                text="Records",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No team data to display for the selected filters.")

    st.subheader("Sample matches")
    if matches.empty:
        st.info("The sample-matches report contains no rows.")
    else:
        st.dataframe(matches, width="stretch", hide_index=True)

with tab2:
    loc = filtered.dropna(subset=["loss_x", "loss_y"]).copy()
    if not loc.empty:
        fig = px.scatter(
            loc,
            x="loss_x",
            y="loss_y",
            color="loss_indicator",
            hover_data=[
                "team_losing_possession",
                "match_id",
                "minute",
                "second",
            ],
            title="Locations of candidate possession-loss events",
            labels={
                "loss_x": "Pitch length coordinate",
                "loss_y": "Pitch width coordinate",
            },
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(xaxis_range=[0, 120], yaxis_range=[80, 0])
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Coordinates use the source event coordinate system; this is not a full pitch drawing."
        )
    else:
        st.info("No location coordinates are available for the selected records.")

with tab3:
    if total:
        outcomes = (
            filtered.groupby("loss_indicator", dropna=False)
            .agg(
                candidate_records=("match_id", "size"),
                next_possession_with_shot=("opponent_possession_contains_shot", "sum"),
            )
            .reset_index()
        )
        outcomes["share_with_shot_pct"] = (
            100 * outcomes["next_possession_with_shot"] / outcomes["candidate_records"]
        ).round(1)
        fig = px.bar(
            outcomes,
            x="loss_indicator",
            y="share_with_shot_pct",
            hover_data=["candidate_records", "next_possession_with_shot"],
            title="Share of candidate records whose next possession contains a shot",
            text="share_with_shot_pct",
        )
        fig.update_layout(
            xaxis_title="Candidate indicator",
            yaxis_title="Records (%)",
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(outcomes, width="stretch", hide_index=True)
        st.caption("Percentages describe association within the filtered sample, not causation.")
    else:
        st.info("No records match the selected filters.")

with tab4:
    st.subheader("Match-level analysis")
    if not filtered.empty:
        available_match_ids = sorted(filtered["match_id"].dropna().astype(int).unique().tolist())
        if available_match_ids:
            chosen_match = st.selectbox("Choose a match ID", available_match_ids)
            match_rows = filtered[filtered["match_id"] == chosen_match].copy()
            match_meta = matches[matches["match_id"] == chosen_match]
            if not match_meta.empty:
                meta = match_meta.iloc[0]
                st.markdown(
                    f"**{meta.get('home_team', 'Unknown')} vs "
                    f"{meta.get('away_team', 'Unknown')}**"
                )
                if {"home_score", "away_score"}.issubset(match_meta.columns):
                    st.caption(
                        f"Final score: {meta.get('home_score', '—')} – {meta.get('away_score', '—')}"
                    )
            m1, m2, m3 = st.columns(3)
            m1.metric("Candidate records", f"{len(match_rows):,}")
            match_shots = int(match_rows["opponent_possession_contains_shot"].sum())
            m2.metric("Next possession contains shot", f"{match_shots:,}")
            match_rate = 100 * match_shots / len(match_rows) if len(match_rows) else 0
            m3.metric("Share with subsequent shot", f"{match_rate:.1f}%")
            if not match_rows.empty:
                timeline = match_rows.copy()
                timeline["event_time_minutes"] = timeline["minute"].fillna(0) + timeline["second"].fillna(0) / 60
                fig = px.scatter(
                    timeline,
                    x="event_time_minutes",
                    y="team_losing_possession",
                    color="loss_indicator",
                    symbol="opponent_possession_contains_shot",
                    hover_data=["loss_event_type", "minute", "second"],
                    title="Candidate events across match time",
                    labels={
                        "event_time_minutes": "Match time (minutes)",
                        "team_losing_possession": "Team",
                        "opponent_possession_contains_shot": "Next possession contains shot",
                    },
                )
                st.plotly_chart(fig, width="stretch")
                st.dataframe(
                    match_rows.sort_values(["minute", "second"], na_position="last"),
                    width="stretch",
                    hide_index=True,
                )
        else:
            st.info("No valid match IDs remain after filtering.")
    else:
        st.info("No records match the selected filters.")

with tab5:
    st.subheader("Validation summary")
    st.json(summary)

    st.subheader("Report integrity")
    integrity = pd.DataFrame(
        [
            {"Check": "Transition report rows", "Result": f"{len(df):,}"},
            {"Check": "Unique matches in transition report", "Result": f"{df['match_id'].nunique():,}"},
            {"Check": "Missing match IDs", "Result": f"{int(df['match_id'].isna().sum()):,}"},
            {"Check": "Missing loss coordinates", "Result": f"{int(df[['loss_x', 'loss_y']].isna().any(axis=1).sum()):,}"},
            {"Check": "Candidate records with next-possession shot", "Result": f"{int(df['opponent_possession_contains_shot'].sum()):,}"},
            {"Check": "Event types represented", "Result": f"{len(coverage):,}"},
        ]
    )
    st.dataframe(integrity, width="stretch", hide_index=True)

    st.subheader("Event type coverage")
    st.dataframe(coverage, width="stretch", hide_index=True)

    st.subheader("Filtered candidate transition records")
    st.caption("Showing up to 500 rows. Use the CSV download for the complete filtered result.")
    st.dataframe(filtered.head(500), width="stretch", hide_index=True)
    st.download_button(
        "Download filtered transition records (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="tactix_filtered_transition_records.csv",
        mime="text/csv",
    )


with tab6:
    st.subheader("Team comparison")
    st.caption(
        "Compare candidate possession-loss indicators and subsequent-shot associations "
        "within the currently selected filters. These are descriptive statistics, not causal effects."
    )

    if filtered.empty:
        st.info("No records match the selected filters. Adjust the sidebar filters to compare teams.")
    else:
        team_comparison = (
            filtered.groupby("team_losing_possession", dropna=False)
            .agg(
                candidate_records=("match_id", "size"),
                next_possession_with_shot=("opponent_possession_contains_shot", "sum"),
                matches_in_sample=("match_id", "nunique"),
            )
            .reset_index()
            .rename(columns={"team_losing_possession": "team"})
        )
        team_comparison["share_with_subsequent_shot_pct"] = (
            100
            * team_comparison["next_possession_with_shot"]
            / team_comparison["candidate_records"]
        ).round(1)

        min_sample = st.slider(
            "Minimum candidate records per team",
            min_value=1,
            max_value=max(1, int(team_comparison["candidate_records"].max())),
            value=min(20, max(1, int(team_comparison["candidate_records"].max()))),
            help="Teams below this sample size are excluded from the chart and table below.",
        )
        comparable = team_comparison[
            team_comparison["candidate_records"] >= min_sample
        ].copy()

        if comparable.empty:
            st.info("No teams meet the selected minimum sample size.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Teams compared", f"{len(comparable):,}")
            c2.metric(
                "Candidate records in comparison",
                f"{int(comparable['candidate_records'].sum()):,}",
            )
            c3.metric(
                "Records followed by a shot",
                f"{int(comparable['next_possession_with_shot'].sum()):,}",
            )

            st.markdown("#### Candidate records by team")
            count_chart = comparable.sort_values("candidate_records", ascending=True)
            fig = px.bar(
                count_chart,
                x="candidate_records",
                y="team",
                orientation="h",
                text="candidate_records",
                hover_data=["matches_in_sample", "next_possession_with_shot"],
                title="Number of candidate possession-loss records",
                labels={
                    "candidate_records": "Candidate records",
                    "team": "Team",
                    "matches_in_sample": "Matches in sample",
                    "next_possession_with_shot": "Next possessions containing a shot",
                },
            )
            st.plotly_chart(fig, width="stretch")

            st.markdown("#### Share with subsequent opponent-possession shot")
            rate_chart = comparable.sort_values(
                "share_with_subsequent_shot_pct", ascending=True
            )
            fig = px.bar(
                rate_chart,
                x="share_with_subsequent_shot_pct",
                y="team",
                orientation="h",
                text="share_with_subsequent_shot_pct",
                hover_data=[
                    "candidate_records",
                    "next_possession_with_shot",
                    "matches_in_sample",
                ],
                title="Percentage of candidate records followed by a shot",
                labels={
                    "share_with_subsequent_shot_pct": "Records followed by a shot (%)",
                    "team": "Team",
                    "candidate_records": "Candidate records (sample size)",
                    "next_possession_with_shot": "Next possessions containing a shot",
                    "matches_in_sample": "Matches in sample",
                },
            )
            st.plotly_chart(fig, width="stretch")

            st.markdown("#### Team comparison table")
            st.dataframe(
                comparable.sort_values(
                    "share_with_subsequent_shot_pct", ascending=False
                ),
                width="stretch",
                hide_index=True,
            )
            st.download_button(
                "Download team comparison (CSV)",
                data=comparable.to_csv(index=False).encode("utf-8"),
                file_name="tactix_team_comparison.csv",
                mime="text/csv",
            )

            st.info(
                "Interpretation: a higher percentage means that a larger share of the "
                "team's candidate records were followed by a shot in the next opponent "
                "possession in this filtered sample. It does not establish that the "
                "candidate loss caused the shot. Comparisons are affected by sample size, "
                "opponents, match context, and the exploratory candidate-event definition."
            )

st.divider()
st.caption(
    "Data source: StatsBomb Open Data. Credit StatsBomb and comply with the "
    "repository's current attribution and usage requirements when sharing results."
)
