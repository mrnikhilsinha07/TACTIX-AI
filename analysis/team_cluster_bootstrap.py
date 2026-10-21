from pathlib import Path

import numpy as np
import pandas as pd

from cluster_bootstrap import load_data


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "transition_candidates.csv"
OUTPUT_FILE = ROOT / "reports" / "team_cluster_bootstrap.csv"

REPLICATES = 5000
CONFIDENCE_LEVEL = 0.95
SEED = 42

TEAM_COLUMN = "team_losing_possession"
MATCH_COLUMN = "match_id"
SUCCESS_COLUMN = "opponent_possession_contains_shot"


def analyze_team(
    team_data: pd.DataFrame,
    replicates: int = REPLICATES,
    seed: int = SEED,
) -> dict:
    """Estimate a team's subsequent-shot rate using match resampling."""

    if replicates < 100:
        raise ValueError("Use at least 100 bootstrap replicates.")

    data = team_data.dropna(
        subset=[MATCH_COLUMN, SUCCESS_COLUMN]
    ).copy()

    if data.empty:
        raise ValueError("No usable records for this team.")

    if not data[SUCCESS_COLUMN].isin([0, 1]).all():
        raise ValueError("Outcomes must be binary.")

    grouped = [
        group[SUCCESS_COLUMN].to_numpy(dtype=float)
        for _, group in data.groupby(MATCH_COLUMN, sort=False)
    ]

    number_of_matches = len(grouped)

    if number_of_matches < 2:
        raise ValueError(
            "At least two distinct matches are required."
        )

    match_successes = np.array(
        [values.sum() for values in grouped],
        dtype=float,
    )

    match_totals = np.array(
        [len(values) for values in grouped],
        dtype=float,
    )

    total_successes = int(match_successes.sum())
    total_records = int(match_totals.sum())

    observed_rate = total_successes / total_records

    rng = np.random.default_rng(seed)

    sampled_indices = rng.integers(
        low=0,
        high=number_of_matches,
        size=(replicates, number_of_matches),
    )

    sampled_successes = match_successes[
        sampled_indices
    ].sum(axis=1)

    sampled_totals = match_totals[
        sampled_indices
    ].sum(axis=1)

    bootstrap_rates = sampled_successes / sampled_totals

    alpha = 1 - CONFIDENCE_LEVEL

    lower = np.quantile(
        bootstrap_rates,
        alpha / 2,
    ) * 100

    upper = np.quantile(
        bootstrap_rates,
        1 - alpha / 2,
    ) * 100

    return {
        "candidate_records": total_records,
        "matches_in_sample": number_of_matches,
        "subsequent_shot_records": total_successes,
        "share_with_subsequent_shot_pct": observed_rate * 100,
        "cluster_ci_lower_pct": float(lower),
        "cluster_ci_upper_pct": float(upper),
        "bootstrap_replicates": replicates,
        "uncertainty_note": (
            "Few matches: interpret cautiously"
            if number_of_matches < 5
            else "Match-clustered interval; exploratory"
        ),
    }


def main():
    data = load_data(INPUT_FILE)

    required = {
        TEAM_COLUMN,
        MATCH_COLUMN,
        SUCCESS_COLUMN,
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    results = []

    for team, team_data in data.groupby(
        TEAM_COLUMN,
        sort=True,
    ):
        result = analyze_team(team_data)
        result["team"] = team
        results.append(result)

    output = pd.DataFrame(results)

    output = output[
        [
            "team",
            "candidate_records",
            "matches_in_sample",
            "subsequent_shot_records",
            "share_with_subsequent_shot_pct",
            "cluster_ci_lower_pct",
            "cluster_ci_upper_pct",
            "bootstrap_replicates",
            "uncertainty_note",
        ]
    ]

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(OUTPUT_FILE, index=False)

    print("\nTACTIX AI — Team-Level Cluster Bootstrap")
    print("=" * 65)
    print(f"Teams analyzed: {len(output)}")
    print(f"Bootstrap replicates per team: {REPLICATES}")
    print(
        output.head(10).round(2).to_string(index=False)
    )
    print(f"\nSaved results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()