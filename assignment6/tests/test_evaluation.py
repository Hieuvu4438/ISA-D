"""Metrics are auditable and use the declared nearest-rank percentile."""
import math

from scripts import run_evaluation


def test_p95_uses_nearest_rank():
    times = list(range(1, 13))
    expected = times[math.ceil(.95 * len(times)) - 1]
    assert run_evaluation.percentile_nearest_rank(times, .95) == expected
