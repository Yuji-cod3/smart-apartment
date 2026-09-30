from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.apartment import Apartment
from backend.app.models.automation import AutomationRule
from backend.app.models.device import Device
from backend.app.models.rent import RentCharge
from backend.app.models.room import Room
from backend.app.models.user import User
from backend.app.schemas.dashboard import DashboardSummary
from backend.app.services.rent import rent_balances
from backend.app.services.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apartments = db.query(Apartment)
    tenants = db.query(User).filter(User.role == "tenant")
    charges = db.query(RentCharge)
    if current_user.role != "admin":
        apartments = apartments.filter(Apartment.id == (current_user.apartment_id or -1))
        tenants = tenants.filter(User.id == current_user.id)
        charges = charges.filter(RentCharge.tenant_id == current_user.id)
    apartment_ids = apartments.with_entities(Apartment.id)
    rooms = db.query(Room).filter(Room.apartment_id.in_(apartment_ids))
    devices = db.query(Device).join(Room).filter(Room.apartment_id.in_(apartment_ids))
    rules = db.query(AutomationRule).filter(AutomationRule.apartment_id.in_(apartment_ids))
    return {
        "apartments": apartments.count(),
        "available_apartments": apartments.filter(Apartment.status == "available").count(),
        "occupied_apartments": apartments.filter(Apartment.status == "occupied").count(),
        "maintenance_apartments": apartments.filter(Apartment.status == "maintenance").count(),
        "tenants": tenants.count(), "active_tenants": tenants.filter(User.is_active.is_(True)).count(),
        "rooms": rooms.count(), "devices": devices.count(),
        "online_devices": devices.filter(Device.is_online.is_(True)).count(),
        "enabled_devices": devices.filter(Device.is_enabled.is_(True)).count(),
        "powered_on_devices": devices.filter(Device.power == "on").count(),
        "automation_rules": rules.count(), "enabled_rules": rules.filter(AutomationRule.is_enabled.is_(True)).count(),
        "rent_balances": rent_balances(charges.all()),
    }
