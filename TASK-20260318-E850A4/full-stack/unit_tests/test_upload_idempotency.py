def finalize_replay_behavior(existing_key: str | None, incoming_key: str) -> str:
    if existing_key is None:
        return "process"
    if existing_key == incoming_key:
        return "replay"
    return "conflict"


def test_upload_finalize_replay_when_same_key():
    assert finalize_replay_behavior("k1", "k1") == "replay"


def test_upload_finalize_conflict_when_different_key_after_commit():
    assert finalize_replay_behavior("k1", "k2") == "conflict"
