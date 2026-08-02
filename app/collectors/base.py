from abc import ABC, abstractmethod
from datetime import date

from app.models import CollectionResult


class BaseCollector(ABC):
    """Base interface for accommodation collectors."""

    @abstractmethod
    def collect(
        self,
        property_id: int,
        listing_url: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> CollectionResult:
        """Collect availability and pricing information for one listing."""

        raise NotImplementedError
