"""Trust/provenance primitives for tool observations."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TrustClass(str, Enum):
    SYSTEM = "system"
    USER = "user"
    TRUSTED_INTERNAL = "trusted_internal"
    EXTERNAL = "external"
    UNTRUSTED = "untrusted"


@dataclass
class DataProvenance:
    source: str
    trust_class: TrustClass
    tainted_fields: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trust_class"] = self.trust_class.value
        return payload


def provenance_for_tool(
    tool_name: str,
    output_trust: str,
    *,
    details: dict[str, Any] | None = None,
) -> DataProvenance:
    try:
        trust = TrustClass(output_trust)
    except ValueError:
        trust = TrustClass.UNTRUSTED
    tainted_fields = ["*"] if trust in {TrustClass.EXTERNAL, TrustClass.UNTRUSTED} else []
    return DataProvenance(
        source=tool_name,
        trust_class=trust,
        tainted_fields=tainted_fields,
        details=details or {},
    )
