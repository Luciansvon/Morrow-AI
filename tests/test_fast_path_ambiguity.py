"""Fast path must share direct-address grammar with collective addressing."""

import pytest

from src.core.types import NormalizedMessage
from src.routing.fast_path import fast_path_router


@pytest.mark.asyncio
async def test_fast_path_does_not_route_role_names_that_are_question_objects():
    result = await fast_path_router.resolve_fast_path(
        NormalizedMessage(
            message_id="fast-role-object",
            group_id="g1",
            sender_id="u1",
            text="apa bedanya manager dan advisor di perusahaan?",
        )
    )
    assert result is None
