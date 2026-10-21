from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "transition_candidates.csv"
OUTPUT_DIR = ROOT / "reports"

BOOTSTRAP_REPLICATES = 5000
CONFIDENCE_LEVEL = 0.95
RANDOM_SEED = 42

MATCH_COLUMN = "match_id"
SUCCESS_COLUMN = "opponent_possession_contains_shot"


# --------------------------------------------------
# Load and validate data
# --------------------------------------------------

def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    data = pd.read_csv(path)

    required_columns = {
        MATCH_COLUMN,
        SUCCESS_COLUMN,
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing)}"
        )

    data = data.dropna(subset=[MATCH_COLUMN]).copy()

    # Parse boolean values safely.
    if pd.api.types.is_bool_dtype(data[SUCCESS_COLUMN]):
        data[SUCCESS_COLUMN] = data[SUCCESS_COLUMN].astype(int)
    else:
        normalized = (
            data[SUCCESS_COLUMN]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        mapping = {
            "true": 1,
            "false": 0,
            "1": 1,
            "0": 0,
        }

        data[SUCCESS_COLUMN] = normalized.map(mapping)

    if data[SUCCESS_COLUMN].isna().any():
        raise ValueError(
            f"{SUCCESS_COLUMN} contains missing or unrecognized values."
        )

    if not data[SUCCESS_COLUMN].isin([0, 1]).all():
        raise ValueError(
            f"{SUCCESS_COLUMN} must contain only binary outcomes."
        )

    data[SUCCESS_COLUMN] = data[SUCCESS_COLUMN].astype(int)

    if data.empty:
        raise ValueError("No usable records remain after validation.")

    return data


# --------------------------------------------------
# Match-clustered bootstrap
# --------------------------------------------------

def cluster_bootstrap_rate(
    data: pd.DataFrame,
    replicates: int = BOOTSTRAP_REPLICATES,
    confidence_level: float = CONFIDENCE_LEVEL,
    seed: int = RANDOM_SEED,
) -> dict:
    """
    Estimate the overall event rate and its match-clustered
    percentile bootstrap confidence interval.

    Each replicate samples whole matches with replacement.
    All records belonging to each selected match are retained.

    Matches receive equal probability of selection, while the
    estimated rate is calculated over all records in the sampled
    matches. Consequently, matches with more candidate records
    contribute more records to each replicate's rate.
    """

    if replicates < 100:
        raise ValueError("Use at least 100 bootstrap replicates.")

    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")

    required = {MATCH_COLUMN, SUCCESS_COLUMN}
    if not required.issubset(data.columns):
        raise ValueError(f"Input must contain {sorted(required)}.")

    clean = data.dropna(subset=[MATCH_COLUMN]).copy()

    if clean.empty:
        raise ValueError("No usable records to analyze.")

    outcomes = clean[SUCCESS_COLUMN].to_numpy()

    if not np.isin(outcomes, [0, 1]).all():
        raise ValueError("Outcomes must be binary values 0 and 1.")

    grouped = [
        group[SUCCESS_COLUMN].to_numpy(dtype=float)
        for _, group in clean.groupby(MATCH_COLUMN, sort=False)
    ]

    number_of_matches = len(grouped)

    if number_of_matches < 2:
        raise ValueError(
            "At least two distinct matches are required for "
            "clustered bootstrap analysis."
        )

    match_successes = np.array(
        [values.sum() for values in grouped],
        dtype=float,
    )

    match_totals = np.array(
        [len(values) for values in grouped],
        dtype=float,
    )

    total_successes = float(match_successes.sum())
    total_records = float(match_totals.sum())
    observed_rate = total_successes / total_records

    rng = np.random.default_rng(seed)

    sampled_match_indices = rng.integers(
        low=0,
        high=number_of_matches,
        size=(replicates, number_of_matches),
    )

    bootstrap_successes = match_successes[
        sampled_match_indices
    ].sum(axis=1)

    bootstrap_totals = match_totals[
        sampled_match_indices
    ].sum(axis=1)

    bootstrap_rates = bootstrap_successes / bootstrap_totals

    alpha = 1 - confidence_level

    lower = float(
        np.quantile(bootstrap_rates, alpha / 2) * 100
    )

    upper = float(
        np.quantile(bootstrap_rates, 1 - alpha / 2) * 100
    )

    return {
        "records": int(total_records),
        "matches": int(number_of_matches),
        "successes": int(total_successes),
        "rate_pct": observed_rate * 100,
        "cluster_ci_lower_pct": lower,
        "cluster_ci_upper_pct": upper,
        "confidence_level": confidence_level,
        "bootstrap_replicates": replicates,
        "method": "Match-clustered percentile bootstrap",
    }


# --------------------------------------------------
# Run analysis
# --------------------------------------------------

def main() -> None:
    data = load_data(INPUT_FILE)

    result = cluster_bootstrap_rate(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "cluster_bootstrap_summary.csv"

    pd.DataFrame([result]).to_csv(output_file, index=False)

    print("\nTACTIX AI — Match-Clustered Bootstrap")
    print("-" * 48)
    print(f"Candidate records: {result['records']:,}")
    print(f"Matches: {result['matches']}")
    print(f"Subsequent-shot records: {result['successes']:,}")
    print(f"Observed rate: {result['rate_pct']:.2f}%")
    print(
        "Clustered 95% confidence interval: "
        f"{result['cluster_ci_lower_pct']:.2f}%–"
        f"{result['cluster_ci_upper_pct']:.2f}%"
    )
    print(f"Bootstrap replicates: {result['bootstrap_replicates']:,}")
    print(f"Saved results to: {output_file}")


if __name__ == "__main__":
    main()