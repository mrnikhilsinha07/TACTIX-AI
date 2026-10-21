import unittest

import pandas as pd

from cluster_bootstrap import cluster_bootstrap_rate, load_data


class TestClusterBootstrap(unittest.TestCase):

    def setUp(self):
        self.data = pd.DataFrame({
            "match_id": [
                1, 1, 1, 1,
                2, 2, 2, 2,
                3, 3, 3, 3,
                4, 4, 4, 4,
            ],
            "opponent_possession_contains_shot": [
                1, 0, 0, 1,
                1, 0, 0, 0,
                0, 0, 0, 1,
                0, 1, 0, 0,
            ],
        })

    def test_observed_rate_is_correct(self):
        result = cluster_bootstrap_rate(
            self.data,
            replicates=1000,
            seed=42,
        )

        self.assertAlmostEqual(result["rate_pct"], 31.25)
        self.assertEqual(result["records"], 16)
        self.assertEqual(result["matches"], 4)
        self.assertEqual(result["successes"], 5)

    def test_interval_bounds_are_ordered(self):
        result = cluster_bootstrap_rate(
            self.data,
            replicates=1000,
            seed=42,
        )

        self.assertLessEqual(
            result["cluster_ci_lower_pct"],
            result["rate_pct"],
        )
        self.assertLessEqual(
            result["rate_pct"],
            result["cluster_ci_upper_pct"],
        )

    def test_fixed_seed_is_reproducible(self):
        first = cluster_bootstrap_rate(
            self.data,
            replicates=1000,
            seed=123,
        )
        second = cluster_bootstrap_rate(
            self.data,
            replicates=1000,
            seed=123,
        )

        self.assertEqual(
            first["cluster_ci_lower_pct"],
            second["cluster_ci_lower_pct"],
        )
        self.assertEqual(
            first["cluster_ci_upper_pct"],
            second["cluster_ci_upper_pct"],
        )

    def test_rejects_too_few_replicates(self):
        with self.assertRaises(ValueError):
            cluster_bootstrap_rate(
                self.data,
                replicates=50,
            )

    def test_rejects_single_match(self):
        single_match = self.data[
            self.data["match_id"] == 1
        ]

        with self.assertRaises(ValueError):
            cluster_bootstrap_rate(single_match)

    def test_rejects_nonbinary_outcomes(self):
        invalid_data = self.data.copy()
        invalid_data.loc[0, "opponent_possession_contains_shot"] = 2

        with self.assertRaises(ValueError):
            cluster_bootstrap_rate(invalid_data)

    def test_load_data_rejects_missing_file(self):
        from pathlib import Path

        with self.assertRaises(FileNotFoundError):
            load_data(Path("file_that_does_not_exist.csv"))

if __name__ == "__main__":
    unittest.main(verbosity=2)