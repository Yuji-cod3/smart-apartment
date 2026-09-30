from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.models.automation import AutomationRule
from backend.app.models.device import Device
from backend.app.models.room import Room
from backend.app.services.devices import control_unavailable_reason, set_power


def evaluate_rules(db: Session, apartment_id: int, source_device_id: int | None = None):
    """One snapshot, ascending rule ID, first eligible rule per target wins.

    Never recursively evaluate actions. Explicit flush includes the initiating
    command in the snapshot, even though the application's sessions disable autoflush.
    """
    db.flush()
    devices = {d.id: d for d in db.query(Device).join(Room).filter(Room.apartment_id == apartment_id).all()}
    snapshot = {key: (d.power, control_unavailable_reason(d)) for key, d in devices.items()}
    rules = db.query(AutomationRule).filter(AutomationRule.apartment_id == apartment_id)
    if source_device_id is not None:
        rules = rules.filter(AutomationRule.source_device_id == source_device_id)
    results, claimed = [], set()
    for rule in rules.order_by(AutomationRule.id).all():
        source = snapshot.get(rule.source_device_id)
        target = snapshot.get(rule.target_device_id)
        if not rule.is_enabled:
            outcome = "disabled"
        elif not source or not target or source[1] or target[1]:
            outcome = "unavailable"
        elif source[0] != rule.source_power:
            outcome = "not_matched"
        elif rule.target_device_id in claimed:
            outcome = "conflict"
        else:
            claimed.add(rule.target_device_id)
            outcome = "applied" if set_power(devices[rule.target_device_id], rule.target_power) else "unchanged"
        results.append({"rule_id": rule.id, "outcome": outcome})
    return {"results": results}


def remove_device_rules(db: Session, device_ids: list[int]) -> None:
    db.query(AutomationRule).filter(or_(
        AutomationRule.source_device_id.in_(device_ids),
        AutomationRule.target_device_id.in_(device_ids),
    )).delete(synchronize_session="fetch")
