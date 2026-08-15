"""Fail-closed tool policy: only explicitly classified actions may execute."""

INTERNAL_ACTIONS: set[str] = {
    "create_task",
    "delegate_task",
    "update_task_status",
    "read_attachment",
    "analyze_campaign",
    "create_content_brief",
    "evaluate_risk",
    "propose_decision",
    "query_memory",
    "calculate",
}

EXTERNAL_ACTIONS: set[str] = {
    "send_email",
    "send_external_message",
    "modify_calendar",
    "post_social_media",
    "execute_transaction",
    "modify_external_account",
    "destructive_external_write",
    "browser_commit_action",
}


class ToolPolicy:
    @staticmethod
    def classify(action_type: str) -> str:
        if action_type in INTERNAL_ACTIONS:
            return "internal"
        if action_type in EXTERNAL_ACTIONS:
            return "external"
        return "unknown"

    @classmethod
    def requires_user_approval(cls, action_type: str) -> bool:
        return cls.classify(action_type) == "external"

    @classmethod
    def is_internal_action(cls, action_type: str) -> bool:
        return cls.classify(action_type) == "internal"


tool_policy = ToolPolicy()
