import math
import unittest


def wilson_interval(successes, total, z=1.96):
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


class WilsonIntervalTests(unittest.TestCase):
    def test_balanced_sample(self):
        low, high = wilson_interval(50, 100)
        self.assertAlmostEqual(low, 40.4, places=1)
        self.assertAlmostEqual(high, 59.6, places=1)

    def test_all_failures(self):
        low, high = wilson_interval(0, 20)
        self.assertEqual(low, 0)
        self.assertGreater(high, 0)

    def test_all_successes(self):
        low, high = wilson_interval(20, 20)
        self.assertLess(low, 100)
        self.assertEqual(high, 100)

    def test_invalid_zero_denominator(self):
        low, high = wilson_interval(0, 0)
        self.assertTrue(math.isnan(low))
        self.assertTrue(math.isnan(high))

    def test_invalid_counts(self):
        self.assertTrue(math.isnan(wilson_interval(5, 4)[0]))
        self.assertTrue(math.isnan(wilson_interval(-1, 4)[0]))

    def test_larger_sample_has_narrower_interval(self):
        low_small, high_small = wilson_interval(5, 10)
        low_large, high_large = wilson_interval(50, 100)
        self.assertGreater(high_small - low_small, high_large - low_large)


if __name__ == "__main__":
    unittest.main()
