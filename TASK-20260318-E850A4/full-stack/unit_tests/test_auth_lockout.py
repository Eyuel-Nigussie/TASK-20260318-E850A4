def lockout_after_failures(failed_count: int, threshold: int = 10) -> bool:
    return failed_count >= threshold


def test_auth_lockout_triggered_on_threshold():
    assert lockout_after_failures(10) is True


def test_auth_lockout_not_triggered_below_threshold():
    assert lockout_after_failures(9) is False
