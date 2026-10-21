from pathlib import Path
import json
import math

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

def wilson_interval(successes, total, z=1.96):
    """Return the Wilson score 95% confidence interval as percentages."""
    try:
        n = int(total)
        x = int(successes)
    except (TypeError, ValueError, OverflowError):
        return (float("nan"), float("nan"))
    if n <= 0 or x < 0 or x > n:
        return (float("nan"), float("nan"))
    p = x / n
    z2 = z * z
    denominator = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denominator
    margin = (z * math.sqrt((p * (1 - p) / n) + (z2 / (4 * n * n)))) / denominator
    return (100 * max(0.0, center - margin), 100 * min(1.0, center + margin))


def add_wilson_intervals(frame, successes_col, total_col, prefix=""):
    """Add Wilson 95% confidence interval columns to an aggregate DataFrame."""
    intervals = [
        wilson_interval(successes, total)
        for successes, total in zip(frame[successes_col], frame[total_col])
    ]
    low_name = f"{prefix}ci95_lower_pct"
    high_name = f"{prefix}ci95_upper_pct"
    frame[low_name] = [round(low, 1) if pd.notna(low) else float("nan") for low, _ in intervals]
    frame[high_name] = [round(high, 1) if pd.notna(high) else float("nan") for _, high in intervals]
    return frame


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
overall_ci_low, overall_ci_high = wilson_interval(with_shot, total)
if total:
    st.caption(
        f"Overall subsequent-shot share: {shot_rate:.1f}% "
        f"(Wilson 95% confidence interval: {overall_ci_low:.1f}%–{overall_ci_high:.1f}%; "
        f"n={total:,} candidate records). The interval assumes independent Bernoulli outcomes; "
        "events from the same match may be correlated."
    )

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "Overview",
        "Where possession was lost",
        "Transition outcomes",
        "Match analysis",
        "Data quality",
        "Team comparison",
        "Advanced analytics",
    ]
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
        team_comparison = add_wilson_intervals(
            team_comparison, "next_possession_with_shot", "candidate_records"
        )

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
                    "ci95_lower_pct",
                    "ci95_upper_pct",
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
            st.caption(
                "95% Wilson confidence intervals quantify binomial sampling uncertainty; "
                "they do not adjust for clustering by match or differences in opposition."
            )
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



with tab7:
    st.subheader("Advanced analytics")
    st.caption(
        "Explore team-by-match patterns and candidate loss indicators. "
        "All rates are descriptive associations, not causal effects."
    )

    if filtered.empty:
        st.info("No records match the selected filters. Adjust the sidebar filters to continue.")
    else:
        # Team-by-match view: use only columns available in the current report.
        st.markdown("#### Team performance by match")
        group_columns = ["match_id", "team_losing_possession"]
        team_match = (
            filtered.groupby(group_columns, dropna=False)
            .agg(
                candidate_records=("match_id", "size"),
                next_possession_with_shot=("opponent_possession_contains_shot", "sum"),
            )
            .reset_index()
            .rename(columns={"team_losing_possession": "team"})
        )
        team_match["share_with_subsequent_shot_pct"] = (
            100 * team_match["next_possession_with_shot"] / team_match["candidate_records"]
        ).round(1)
        team_match = add_wilson_intervals(
            team_match, "next_possession_with_shot", "candidate_records"
        )

        # Add match metadata where available, without assuming optional columns exist.
        metadata_columns = [
            column for column in ["match_id", "match_date", "home_team", "away_team"]
            if column in matches.columns
        ]
        if "match_id" in metadata_columns:
            metadata = matches[metadata_columns].drop_duplicates(subset=["match_id"])
            team_match = team_match.merge(metadata, on="match_id", how="left")
            if {"home_team", "away_team"}.issubset(team_match.columns):
                team_match["match_label"] = (
                    team_match["home_team"].fillna("Unknown")
                    + " vs "
                    + team_match["away_team"].fillna("Unknown")
                    + " ("
                    + team_match["match_id"].astype(str)
                    + ")"
                )
            else:
                team_match["match_label"] = team_match["match_id"].astype(str)
        else:
            team_match["match_label"] = team_match["match_id"].astype(str)

        teams_in_filtered = sorted(team_match["team"].dropna().unique().tolist())
        chosen_teams = st.multiselect(
            "Teams to inspect by match",
            options=teams_in_filtered,
            default=teams_in_filtered[: min(5, len(teams_in_filtered))],
            key="advanced_match_teams",
        )
        team_match_view = team_match[team_match["team"].isin(chosen_teams)].copy()

        if team_match_view.empty:
            st.info("Select at least one team to view match-by-match results.")
        else:
            team_match_view = team_match_view.sort_values(
                ["team", "match_id"], na_position="last"
            )
            fig = px.scatter(
                team_match_view,
                x="match_label",
                y="share_with_subsequent_shot_pct",
                color="team",
                size="candidate_records",
                hover_data=[
                    "match_id",
                    "candidate_records",
                    "next_possession_with_shot",
                    "share_with_subsequent_shot_pct",
                ],
                title="Subsequent-shot share by team and match",
                labels={
                    "match_label": "Match",
                    "share_with_subsequent_shot_pct": "Records followed by a shot (%)",
                    "team": "Team",
                    "candidate_records": "Candidate records (bubble size)",
                    "next_possession_with_shot": "Records followed by a shot",
                },
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, width="stretch")
            st.dataframe(team_match_view, width="stretch", hide_index=True)
            st.download_button(
                "Download team-by-match results (CSV)",
                data=team_match_view.to_csv(index=False).encode("utf-8"),
                file_name="tactix_team_match_analysis.csv",
                mime="text/csv",
            )

        st.divider()
        st.markdown("#### Candidate loss-indicator analysis")
        indicator_analysis = (
            filtered.groupby("loss_indicator", dropna=False)
            .agg(
                candidate_records=("match_id", "size"),
                next_possession_with_shot=("opponent_possession_contains_shot", "sum"),
                teams_in_sample=("team_losing_possession", "nunique"),
                matches_in_sample=("match_id", "nunique"),
            )
            .reset_index()
            .rename(columns={"loss_indicator": "candidate_loss_indicator"})
        )
        indicator_analysis["share_with_subsequent_shot_pct"] = (
            100
            * indicator_analysis["next_possession_with_shot"]
            / indicator_analysis["candidate_records"]
        ).round(1)
        indicator_analysis = add_wilson_intervals(
            indicator_analysis, "next_possession_with_shot", "candidate_records"
        )

        min_indicator_sample = st.slider(
            "Minimum records per loss indicator",
            min_value=1,
            max_value=max(1, int(indicator_analysis["candidate_records"].max())),
            value=min(10, max(1, int(indicator_analysis["candidate_records"].max()))),
            key="advanced_indicator_min_sample",
            help="Indicators below this sample size are excluded from the chart and table.",
        )
        indicator_view = indicator_analysis[
            indicator_analysis["candidate_records"] >= min_indicator_sample
        ].copy()

        if indicator_view.empty:
            st.info("No loss indicators meet the selected minimum sample size.")
        else:
            indicator_view = indicator_view.sort_values(
                "share_with_subsequent_shot_pct", ascending=True
            )
            fig = px.bar(
                indicator_view,
                x="share_with_subsequent_shot_pct",
                y="candidate_loss_indicator",
                orientation="h",
                text="share_with_subsequent_shot_pct",
                hover_data=[
                    "candidate_records",
                    "next_possession_with_shot",
                    "teams_in_sample",
                    "matches_in_sample",
                    "ci95_lower_pct",
                    "ci95_upper_pct",
                ],
                title="Subsequent-shot share by candidate loss indicator",
                labels={
                    "share_with_subsequent_shot_pct": "Records followed by a shot (%)",
                    "candidate_loss_indicator": "Candidate loss indicator",
                    "candidate_records": "Candidate records (sample size)",
                    "next_possession_with_shot": "Records followed by a shot",
                    "teams_in_sample": "Teams represented",
                    "matches_in_sample": "Matches represented",
                },
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(
                indicator_view.sort_values(
                    "share_with_subsequent_shot_pct", ascending=False
                ),
                width="stretch",
                hide_index=True,
            )
            st.download_button(
                "Download loss-indicator analysis (CSV)",
                data=indicator_view.to_csv(index=False).encode("utf-8"),
                file_name="tactix_loss_indicator_analysis.csv",
                mime="text/csv",
            )

        st.info(
            "Interpretation: these summaries describe how often candidate records are "
            "followed by a shot-containing opponent possession in the available sample. "
            "They do not establish causation, and differences can reflect opponent quality, "
            "match context, repeated events, and the exploratory candidate-event definition. "
            "Wilson intervals assume independent binary outcomes and may be too narrow when "
            "events are correlated within matches."
        )

st.divider()
st.caption(
    "Data source: StatsBomb Open Data. Credit StatsBomb and comply with the "
    "repository's current attribution and usage requirements when sharing results."
)
