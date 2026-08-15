from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class RoleID(str, Enum):
    MANAGER = "manager"
    MARKETING = "marketing"
    ADVISOR = "advisor"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class MemoryScope(str, Enum):
    ROLE = "role"
    SHARED = "shared"


class MemoryType(str, Enum):
    FACT = "fact"
    DECISION = "decision"
    CONSTRAINT = "constraint"
    STATUS = "status"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class WorkloadType(str, Enum):
    CASUAL = "casual"
    ROUTINE = "routine"
    PLANNING = "planning"
    COMPLEX_PLANNING = "complex_planning"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class AddressingType(str, Enum):
    NONE = "none"                       # Bukan sapaan agen (misal: "hitung semua harga ini")
    SINGLE_AGENT = "single_agent"       # 1 agen spesifik (misal: "Manager, cek task ini")
    MULTIPLE_AGENTS = "multiple_agents" # Subset agen (misal: "Manager dan Marketing, halo")
    ALL_AGENTS = "all_agents"           # Seluruh tim (misal: "halo semua", "hai tim")


class MessageIntent(str, Enum):
    SOCIAL = "social"                   # Sapaan, basa-basi, cek kehadiran
    WORK_REQUEST = "work_request"       # Permintaan tugas kerja / strategi
    QUESTION = "question"               # Pertanyaan seputar status / informasi
    COMMAND = "command"                 # Perintah tindakan eksternal
    OTHER = "other"


class AddressingResult(BaseModel):
    addressing_type: AddressingType
    target_agents: list[RoleID] = Field(default_factory=list)
    intent: MessageIntent = MessageIntent.WORK_REQUEST
    allow_multi_response: bool = False
    requires_coordinator: bool = False
    coordinator: RoleID | None = None
    confidence: float = 1.0


class ModalityType(str, Enum):
    TEXT = "text"
    MULTIMODAL = "multimodal"


class AttachmentInfo(BaseModel):
    file_id: str
    original_name: str
    detected_mime: str
    file_path: str
    file_size: int
    is_supported: bool = True
    extracted_text: str | None = None
    structured_data: dict[str, Any] | None = None
    visual_description: str | None = None
    error_message: str | None = None


class NormalizedMessage(BaseModel):
    message_id: str
    group_id: str
    sender_id: str
    sender_name: str = ""
    text: str = ""
    reply_to_message_id: str | None = None
    received_by_bot_role: RoleID | None = None
    bot_identity: str | None = None
    attachments: list[AttachmentInfo] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
    raw_event: dict[str, Any] | None = None


class TaskModel(BaseModel):
    id: str
    title: str
    description: str = ""
    current_owner: RoleID
    status: TaskStatus = TaskStatus.TODO
    dependencies: list[str] = Field(default_factory=list)
    attempted_agents: list[RoleID] = Field(default_factory=list)
    retry_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MemoryItem(BaseModel):
    id: str
    scope: MemoryScope
    role_id: RoleID | None = None
    key: str
    value: str
    memory_type: MemoryType = MemoryType.FACT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ApprovalRequest(BaseModel):
    approval_id: str
    action_type: str
    normalized_parameters: dict[str, Any]
    parameter_hash: str
    requested_by_role: RoleID
    idempotency_key: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    approved_by: str | None = None
    execution_id: str | None = None


class LLMUsageRecord(BaseModel):
    request_id: str
    task_id: str | None = None
    role_id: str | None = None
    model: str
    provider: str = "openrouter"
    input_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=utc_now)
