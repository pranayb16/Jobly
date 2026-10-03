from jobly.jobs.repository import evaluate_mass_drop, trusted_job_count


def test_zero_job_guard_preserves_previous_jobs():
    decision = evaluate_mass_drop(5, 0)
    assert decision.allowed is False


def test_large_partial_drop_is_suspicious():
    decision = evaluate_mass_drop(500, 8)
    assert decision.allowed is False
    assert "mass-drop" in decision.reason


def test_threshold_boundary_is_allowed():
    assert evaluate_mass_drop(100, 25).allowed is True


def test_moderate_change_is_allowed():
    assert evaluate_mass_drop(100, 70).allowed is True


def test_small_board_partial_change_is_allowed():
    assert evaluate_mass_drop(10, 2).allowed is True


def test_anomaly_does_not_replace_trusted_baseline():
    first = evaluate_mass_drop(500, 8)
    baseline = trusted_job_count(500, 8, deactivation_allowed=first.allowed)
    assert baseline == 500


def test_consecutive_anomaly_still_uses_trusted_baseline():
    first = evaluate_mass_drop(500, 8)
    baseline = trusted_job_count(500, 8, deactivation_allowed=first.allowed)
    second = evaluate_mass_drop(baseline, 8)
    assert second.allowed is False
    assert "previous_job_count=500" in second.reason
