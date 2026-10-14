"""Tests for the default autonomous engineering guidance."""
from types import SimpleNamespace

from agent import system_prompt


def _agent(**overrides):
    values = {
        "valid_tool_names": {"terminal", "skill_view"},
        "_task_completion_guidance": False,
        "_parallel_tool_call_guidance": False,
        "_tool_use_enforcement": False,
        "_execution_guidance": False,
        "model": "test-model",
        "provider": "",
        "platform": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_engineering_guidance_is_enabled_by_default_when_tools_exist(monkeypatch):
    monkeypatch.setattr(system_prompt, "_tool_guidance_block", lambda _agent: "")
    parts = system_prompt._guidance_parts(_agent())

    assert any("Autonomous engineering workflow" in part for part in parts)
    guidance = next(part for part in parts if "Autonomous engineering workflow" in part)
    assert "research" in guidance
    assert "acceptance criteria" in guidance
    assert "NOT VERIFIED" in guidance
    assert "explicit approval" in guidance


def test_guidance_does_not_inject_without_tools(monkeypatch):
    monkeypatch.setattr(system_prompt, "_tool_guidance_block", lambda _agent: "")
    parts = system_prompt._guidance_parts(_agent(valid_tool_names=set()))

    assert not any("Autonomous engineering workflow" in part for part in parts)
