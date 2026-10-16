import pytest

from app.agents.tools import AgentToolError, ToolCall, agent_tools
from app.schemas.chat import ChatMessage


def test_agent_plan_uses_read_only_tools_for_urls_and_search() -> None:
    calls = agent_tools.plan(
        [ChatMessage(role="user", content="Review example.com and find recent coverage")],
        use_web_search=True,
    )

    assert [call.name for call in calls] == ["crawl_website", "web_search"]
    assert all(
        tool.permission == "read_only" for tool in agent_tools.registry.metadata()
    )


def test_agent_plan_skips_tools_for_local_chat() -> None:
    calls = agent_tools.plan(
        [ChatMessage(role="user", content="Help me draft a title")],
        use_web_search=False,
    )

    assert calls == []


@pytest.mark.asyncio
async def test_registry_rejects_unknown_tools() -> None:
    with pytest.raises(AgentToolError, match="Unknown tool"):
        await agent_tools.execute(
            ToolCall(
                id="unknown-1",
                name="unknown",
                label="Unknown",
                arguments={},
            )
        )
