from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.conversations import delete_conversation
from app.models import Conversation


@pytest.mark.asyncio
async def test_delete_conversation_removes_it_and_commits() -> None:
    conversation = Conversation(id=uuid4(), title="Old chat", model="qwen2.5:3b")
    session = AsyncMock()
    session.get.return_value = conversation

    response = await delete_conversation(conversation.id, session)

    assert response.status_code == 204
    session.delete.assert_awaited_once_with(conversation)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_conversation_returns_not_found() -> None:
    session = AsyncMock()
    session.get.return_value = None

    with pytest.raises(HTTPException) as error:
        await delete_conversation(uuid4(), session)

    assert error.value.status_code == 404
    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()
