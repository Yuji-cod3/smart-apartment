from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.apartment import Apartment
from backend.app.models.automation import AutomationRule
from backend.app.models.device import Device
from backend.app.models.room import Room
from backend.app.models.user import User
from backend.app.schemas.automation import AutomationCreate, AutomationResponse, AutomationEvaluation
from backend.app.services.authorization import require_admin
from backend.app.services.security import get_current_user
from backend.app.services.devices import CONTROLLABLE_TYPES, require_apartment_access
from backend.app.services.automation import evaluate_rules

router = APIRouter(prefix="/apartments/{apartment_id}/automations", tags=["Automations"])


def check_apartment(db, apartment_id, user):
    if db.get(Apartment, apartment_id) is None:
        raise HTTPException(404, "Apartment not found.")
    require_apartment_access(user, apartment_id)


def validate_devices(db, apartment_id, data):
    for device_id in (data.source_device_id, data.target_device_id):
        device = db.query(Device).join(Room).filter(
            Device.id == device_id, Room.apartment_id == apartment_id,
        ).first()
        if device is None:
            raise HTTPException(404, "Rule device not found in this apartment.")
        if device.type not in CONTROLLABLE_TYPES:
            raise HTTPException(422, "Rule devices must support power control.")


def find_rule(db, apartment_id, rule_id):
    rule = db.query(AutomationRule).filter_by(id=rule_id, apartment_id=apartment_id).first()
    if rule is None:
        raise HTTPException(404, "Automation rule not found.")
    return rule


@router.get("/", response_model=list[AutomationResponse])
def list_rules(apartment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_apartment(db, apartment_id, current_user)
    return db.query(AutomationRule).filter_by(apartment_id=apartment_id).order_by(AutomationRule.id).all()


@router.post("/", response_model=AutomationResponse, status_code=201)
def create_rule(apartment_id: int, data: AutomationCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    check_apartment(db, apartment_id, current_user)
    validate_devices(db, apartment_id, data)
    rule = AutomationRule(apartment_id=apartment_id, **data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/evaluate", response_model=AutomationEvaluation)
def evaluate(apartment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_apartment(db, apartment_id, current_user)
    result = evaluate_rules(db, apartment_id)
    db.commit()
    return result


@router.put("/{rule_id}", response_model=AutomationResponse)
def replace_rule(apartment_id: int, rule_id: int, data: AutomationCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    check_apartment(db, apartment_id, current_user)
    rule = find_rule(db, apartment_id, rule_id)
    validate_devices(db, apartment_id, data)
    for key, value in data.model_dump().items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(apartment_id: int, rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    check_apartment(db, apartment_id, current_user)
    db.delete(find_rule(db, apartment_id, rule_id))
    db.commit()
