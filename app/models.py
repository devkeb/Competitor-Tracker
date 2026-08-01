from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal


AvailabilityStatus = Literal[
    "available",
    "not_bookable",
    "unknown",
    "error",
]


@dataclass
class CollectionResult:
    status: AvailabilityStatus
    currency: str | None = None
    nightly_price: Decimal | None = None
    total_price: Decimal | None = None
    cleaning_fee: Decimal | None = None
    service_fee: Decimal | None = None
    rating: Decimal | None = None
    review_count: int | None = None
    minimum_nights: int | None = None
    result_message: str | None = None
    screenshot_path: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)