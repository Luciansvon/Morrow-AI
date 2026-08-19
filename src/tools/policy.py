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
    "current_datetime",
    "morrow_tool_search",
    "browser_open",
    "browser_snapshot",
    "browser_screenshot",
    "browser_fill",
    "browser_type",
    "browser_select",
    "browser_check",
    "browser_uncheck",
    "browser_scroll",
    "openviking_find",
    "openviking_read",
    "immich_search_assets",
    "immich_get_asset",
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
    "browser_click",
    "browser_press",
    "openviking_add_resource",
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
