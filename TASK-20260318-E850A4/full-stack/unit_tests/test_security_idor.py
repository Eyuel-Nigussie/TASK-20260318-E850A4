def can_access_registration(owner_user_id: int, requester_user_id: int) -> bool:
    return owner_user_id == requester_user_id


def test_idor_denied_when_user_ids_differ():
    assert can_access_registration(owner_user_id=100, requester_user_id=101) is False


def test_idor_allowed_for_owner():
    assert can_access_registration(owner_user_id=100, requester_user_id=100) is True
