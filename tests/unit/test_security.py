from shared.telemed_common.security import sign_token, verify_token


def test_token_sign_and_verify() -> None:
    token = sign_token({"sub": "PAT-1", "role": "patient"}, "secret", exp_minutes=10)
    payload = verify_token(token, "secret")
    assert payload is not None
    assert payload["sub"] == "PAT-1"
