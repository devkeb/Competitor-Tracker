class AirbnbExtractor:
    def __init__(self):
        self.selectors = {
            "property_card": '[data-testid="card-container"]',
            "property_name": '[data-testid="listing-card-title"]',
            "price": '[data-testid="price-availability-row"]',
            "rating": '[aria-label*="rating"]',
            "link": "a",
        }