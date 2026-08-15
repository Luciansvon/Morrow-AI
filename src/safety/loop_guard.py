"""Atomic loop guard untuk diskusi otomatis antar agen."""

import json

from src.core.types import RoleID
from src.storage.sqlite import db


class LoopGuard:
    MAX_TURNS = 4
    MAX_AGENTS = 3

    @staticmethod
    async def can_continue_discussion(
        thread_id: str,
        group_id: str,
        proposing_role: RoleID,
    ) -> tuple[bool, str, int]:
        async with db.transaction() as conn:
            cursor = await conn.execute(
                "SELECT * FROM threads WHERE thread_id=?",
                (thread_id,),
            )
            raw = await cursor.fetchone()
            if not raw:
                await conn.execute(
                    """INSERT INTO threads
                       (thread_id, group_id, active_agents, turn_count, max_turns, status)
                       VALUES (?, ?, ?, 1, ?, 'active')""",
                    (
                        thread_id,
                        group_id,
                        json.dumps([proposing_role.value]),
                        LoopGuard.MAX_TURNS,
                    ),
                )
                return True, "Putaran ke-1 dimulai", 1

            row = dict(raw)
            if row["group_id"] != group_id:
                return False, "Thread berasal dari grup yang berbeda.", row["turn_count"]
            if row["status"] != "active":
                return False, f"Thread sudah berstatus '{row['status']}'.", row["turn_count"]

            turn_count = int(row["turn_count"])
            active_agents = json.loads(row["active_agents"])
            if proposing_role.value not in active_agents:
                if len(active_agents) >= LoopGuard.MAX_AGENTS:
                    await conn.execute(
                        "UPDATE threads SET status='waiting_user' WHERE thread_id=?",
                        (thread_id,),
                    )
                    return (
                        False,
                        f"Batas maksimum {LoopGuard.MAX_AGENTS} agen telah tercapai.",
                        turn_count,
                    )
                active_agents.append(proposing_role.value)

            if turn_count >= LoopGuard.MAX_TURNS:
                await conn.execute(
                    "UPDATE threads SET status='waiting_user' WHERE thread_id=?",
                    (thread_id,),
                )
                return (
                    False,
                    f"Batas maksimal {LoopGuard.MAX_TURNS} putaran diskusi habis. "
                    "Status dialihkan ke 'waiting_user'.",
                    turn_count,
                )

            new_turn = turn_count + 1
            await conn.execute(
                """UPDATE threads SET turn_count=?, active_agents=?
                   WHERE thread_id=? AND status='active'""",
                (new_turn, json.dumps(active_agents), thread_id),
            )
            return True, f"Putaran ke-{new_turn} diizinkan", new_turn


loop_guard = LoopGuard()
