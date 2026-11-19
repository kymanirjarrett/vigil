from anomaly_detection import detect_anomalies


def run(i, seconds, status="SUCCEEDED"):
    return {"run_id": f"jr_{i}", "execution_time": seconds, "status": status,
            "started_on": f"2026-11-18T00:{i:02d}:00Z"}


def types(anomalies):
    return [a["type"] for a in anomalies]


def test_spike_above_two_stdevs_is_flagged():
    runs = [run(0, 900)] + [run(i, 100 + i % 3) for i in range(1, 10)]
    found = detect_anomalies(runs)
    assert types(found) == ["DURATION_SPIKE"]
    assert found[0]["run_id"] == "jr_0"


def test_stable_runs_have_no_false_positive():
    runs = [run(i, 100 + i % 5) for i in range(20)]
    assert detect_anomalies(runs) == []


def test_fewer_than_three_runs_returns_nothing():
    assert detect_anomalies([run(0, 10), run(1, 5000)]) == []


def test_zero_stdev_does_not_flag_or_divide_by_zero():
    assert detect_anomalies([run(i, 120) for i in range(5)]) == []


def test_consecutive_failures_flagged_once():
    runs = [run(0, 100, "FAILED"), run(1, 100, "FAILED"), run(2, 100, "FAILED"),
            run(3, 100), run(4, 100)]
    found = detect_anomalies(runs)
    assert types(found) == ["CONSECUTIVE_FAILURES"]
    assert found[0]["severity"] == "critical"


def test_non_consecutive_failures_are_not_a_streak():
    runs = [run(0, 100, "FAILED"), run(1, 100), run(2, 100, "FAILED"), run(3, 100)]
    assert detect_anomalies(runs) == []
