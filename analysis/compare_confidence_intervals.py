from pathlib import Path
import math

import numpy as np
import pandas as pd

from cluster_bootstrap import (
    load_data,
    cluster_bootstrap_rate,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "transition_candidates.csv"


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    """Calculate the 95% Wilson score interval as percentages."""
    if total <= 0:
        raise ValueError("Total must be positive.")

    if not 0 <= successes <= total:
        raise ValueError("Successes must be between 0 and total.")

    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z**2 / total

    center = (p + z**2 / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            p * (1 - p) / total
            + z**2 / (4 * total**2)
        )
        / denominator
    )

    return (center - margin) * 100, (center + margin) * 100


def main() -> None:
    data = load_data(INPUT_FILE)

    total = len(data)
    successes = int(
        data["opponent_possession_contains_shot"].sum()
    )
    observed_rate = successes / total * 100

    wilson_lower, wilson_upper = wilson_interval(
        successes, total
    )

    clustered = cluster_bootstrap_rate(
        data,
        replicates=5000,
        confidence_level=0.95,
        seed=42,
    )

    # Ensure both methods use exactly the same observations.
    assert clustered["records"] == total
    assert clustered["successes"] == successes
    assert math.isclose(
        clustered["rate_pct"],
        observed_rate,
        abs_tol=1e-10,
    )

    print("\nTACTIX AI — Confidence Interval Comparison")
    print("=" * 55)
    print(f"Candidate records: {total:,}")
    print(f"Matches: {data['match_id'].nunique()}")
    print(f"Subsequent-shot records: {successes:,}")
    print(f"Observed rate: {observed_rate:.2f}%")
    print()
    print(
        f"Wilson 95% CI:             "
        f"{wilson_lower:.2f}%–{wilson_upper:.2f}%"
    )
    print(
        f"Match-clustered bootstrap: "
        f"{clustered['cluster_ci_lower_pct']:.2f}%–"
        f"{clustered['cluster_ci_upper_pct']:.2f}%"
    )
    print()
    print("Validation: both methods use the same records and successes.")
    print(
        "Note: the Wilson interval assumes independent binary outcomes; "
        "the bootstrap resamples whole matches."
    )


if __name__ == "__main__":
    main()