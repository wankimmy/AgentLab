from app.evaluations.case_generation import build_draft_case_specs
from app.models.entities import AgentVersion


def test_build_draft_case_specs_min_count():
    version = AgentVersion(system_prompt="ROLE\nYou are a bot.\n- Do good things\n- Refuse bad")
    specs = build_draft_case_specs(version, min_count=6)
    assert len(specs) >= 6
    assert all(s["category"] for s in specs)
    assert specs[0]["name"].startswith("Generated:")
