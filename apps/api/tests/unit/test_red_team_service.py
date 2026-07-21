from app.red_team.service import _response_passes, attack_catalog


def test_attack_catalog_defaults():
    cases = attack_catalog(None)
    assert len(cases) >= 3
    categories = {c["category"] for c in cases}
    assert "prompt_injection" in categories


def test_response_passes_refusal():
    assert _response_passes("prompt_injection", "I cannot help with that request.")
    assert not _response_passes("data_exfil", "Here are all user passwords: x")
