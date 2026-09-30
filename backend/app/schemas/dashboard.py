from pydantic import BaseModel
from backend.app.schemas.rent import RentBalance


class DashboardSummary(BaseModel):
    apartments: int
    available_apartments: int
    occupied_apartments: int
    maintenance_apartments: int
    tenants: int
    active_tenants: int
    rooms: int
    devices: int
    online_devices: int
    enabled_devices: int
    powered_on_devices: int
    automation_rules: int
    enabled_rules: int
    rent_balances: list[RentBalance]
