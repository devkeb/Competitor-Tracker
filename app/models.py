from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class CollectionResult:
    status: str

    currency: str | None = None
    nightly_price: Decimal | None = None

    result_message: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    screenshot_path: str | None = None