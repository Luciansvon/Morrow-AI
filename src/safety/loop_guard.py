"""Penjaga batas perulangan diskusi otomatis antar agen (Loop Guard)."""

import json

from src.core.types import RoleID
from src.storage.sqlite import db


class LoopGuard:
    """Pembatas putaran diskusi antar agen (maksimal 4 turns, maksimal 3 agents)."""

    MAX_TURNS = 4
    MAX_AGENTS = 3

    @staticmethod
    async def can_continue_discussion(
        thread_id: str,
        group_id: str,
        proposing_role: RoleID,
    ) -> tuple[bool, str, int]:
        """
        Memeriksa apakah diskusi otomatis masih memiliki kuota giliran bicara (AC-014).
        Mengembalikan (can_continue, status_message, current_turn).
        """
        row = await db.fetch_one(
            "SELECT * FROM threads WHERE thread_id = ?",
            (thread_id,),
        )
        if not row:
            # Buat thread baru
            agents_list = [proposing_role.value]
            await db.execute(
                """
                INSERT INTO threads (thread_id, group_id, active_agents, turn_count, max_turns, status)
                VALUES (?, ?, ?, 1, ?, 'active')
                """,
                (thread_id, group_id, json.dumps(agents_list), LoopGuard.MAX_TURNS),
            )
            return True, "Putaran ke-1 dimulai", 1

        turn_count = row["turn_count"]
        active_agents = json.loads(row["active_agents"])

        if proposing_role.value not in active_agents:
            if len(active_agents) >= LoopGuard.MAX_AGENTS:
                return False, f"Batas maksimum {LoopGuard.MAX_AGENTS} agen telah tercapai dalam diskusi ini.", turn_count
            active_agents.append(proposing_role.value)

        # Cek batas giliran (Max 4 Turns)
        if turn_count >= LoopGuard.MAX_TURNS:
            await db.execute(
                "UPDATE threads SET status = 'waiting_user' WHERE thread_id = ?",
                (thread_id,),
            )
            return False, f"Batas maksimal {LoopGuard.MAX_TURNS} putaran diskusi habis. Status dialihkan ke 'waiting_user'.", turn_count

        # Tambah turn count
        new_turn = turn_count + 1
        await db.execute(
            """
            UPDATE threads
            SET turn_count = ?, active_agents = ?
            WHERE thread_id = ?
            """,
            (new_turn, json.dumps(active_agents), thread_id),
        )
        return True, f"Putaran ke-{new_turn} diizinkan", new_turn


loop_guard = LoopGuard()
