import unittest

import pandas as pd

from team_cluster_bootstrap import analyze_team


class TestTeamClusterBootstrap(unittest.TestCase):

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
        result = analyze_team(
            self.data,
            replicates=1000,
            seed=42,
        )

        self.assertEqual(result["candidate_records"], 16)
        self.assertEqual(result["matches_in_sample"], 4)
        self.assertEqual(result["subsequent_shot_records"], 5)
        self.assertAlmostEqual(
            result["share_with_subsequent_shot_pct"],
            31.25,
        )

    def test_interval_contains_observed_rate(self):
        result = analyze_team(
            self.data,
            replicates=1000,
            seed=42,
        )

        rate = result["share_with_subsequent_shot_pct"]

        self.assertLessEqual(
            result["cluster_ci_lower_pct"],
            rate,
        )
        self.assertGreaterEqual(
            result["cluster_ci_upper_pct"],
            rate,
        )

    def test_fixed_seed_is_reproducible(self):
        first = analyze_team(
            self.data,
            replicates=1000,
            seed=123,
        )
        second = analyze_team(
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

    def test_few_matches_are_flagged(self):
        result = analyze_team(
            self.data,
            replicates=1000,
        )

        self.assertEqual(
            result["uncertainty_note"],
            "Few matches: interpret cautiously",
        )

    def test_rejects_too_few_replicates(self):
        with self.assertRaises(ValueError):
            analyze_team(self.data, replicates=50)

    def test_rejects_single_match(self):
        single_match = self.data[
            self.data["match_id"] == 1
        ]

        with self.assertRaises(ValueError):
            analyze_team(single_match)

    def test_rejects_nonbinary_outcomes(self):
        invalid_data = self.data.copy()
        invalid_data.loc[
            0, "opponent_possession_contains_shot"
        ] = 2

        with self.assertRaises(ValueError):
            analyze_team(invalid_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)