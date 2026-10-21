from pathlib import Path

import pandas as pd

from cluster_bootstrap import load_data, cluster_bootstrap_rate


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "transition_candidates.csv"

SEEDS = [11, 42, 123, 2026, 9876]
REPLICATES = 5000


def main():
    data = load_data(INPUT_FILE)
    results = []

    for seed in SEEDS:
        result = cluster_bootstrap_rate(
            data,
            replicates=REPLICATES,
            confidence_level=0.95,
            seed=seed,
        )

        results.append({
            "seed": seed,
            "rate_pct": result["rate_pct"],
            "ci_lower_pct": result["cluster_ci_lower_pct"],
            "ci_upper_pct": result["cluster_ci_upper_pct"],
        })

    comparison = pd.DataFrame(results)

    print("\nBootstrap stability across random seeds")
    print("=" * 65)
    print(comparison.round(4).to_string(index=False))

    print("\nVariation across seeds:")
    print(
        "Lower-bound range:",
        f"{comparison['ci_lower_pct'].min():.4f}%–"
        f"{comparison['ci_lower_pct'].max():.4f}%",
    )
    print(
        "Upper-bound range:",
        f"{comparison['ci_upper_pct'].min():.4f}%–"
        f"{comparison['ci_upper_pct'].max():.4f}%",
    )

    output_file = ROOT / "reports" / "bootstrap_stability.csv"
    comparison.to_csv(output_file, index=False)
    print(f"\nSaved results to: {output_file}")


if __name__ == "__main__":
    main()