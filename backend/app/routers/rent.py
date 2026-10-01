from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.rent import RentCharge
from backend.app.models.user import User
from backend.app.schemas.rent import RentCreate, RentPayment, RentResponse
from backend.app.services.authorization import require_admin
from backend.app.services.security import get_current_user
from backend.app.services.rent import rent_view

router = APIRouter(prefix="/rent", tags=["Rent"])


def scoped_charges(db, user):
    query = db.query(RentCharge)
    return query if user.role == "admin" else query.filter(RentCharge.tenant_id == user.id)


@router.post("/", response_model=RentResponse, status_code=201)
def create_charge(data: RentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    tenant = db.get(User, data.tenant_id)
    if tenant is None:
        raise HTTPException(404, "Tenant not found.")
    if tenant.role != "tenant" or not tenant.is_active or tenant.apartment_id is None:
        raise HTTPException(409, "Rent requires an active tenant assigned to an apartment.")
    charge = RentCharge(apartment_id=tenant.apartment_id, **data.model_dump())
    db.add(charge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A rent charge already exists for this tenant and period.")
    db.refresh(charge)
    return rent_view(charge)


@router.get("/", response_model=list[RentResponse])
def list_charges(
    tenant_id: int | None = Query(default=None, gt=0),
    offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and tenant_id is not None and tenant_id != current_user.id:
        raise HTTPException(403, "Access to this tenant is not permitted.")
    query = scoped_charges(db, current_user)
    if tenant_id is not None:
        query = query.filter(RentCharge.tenant_id == tenant_id)
    return [rent_view(c) for c in query.order_by(RentCharge.due_date.desc(), RentCharge.id.desc()).offset(offset).limit(limit).all()]


@router.get("/{charge_id}", response_model=RentResponse)
def get_charge(charge_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    charge = scoped_charges(db, current_user).filter(RentCharge.id == charge_id).first()
    if charge is None:
        raise HTTPException(404, "Rent charge not found.")
    return rent_view(charge)


@router.put("/{charge_id}/payment", response_model=RentResponse)
def record_payment(charge_id: int, data: RentPayment, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    charge = db.get(RentCharge, charge_id)
    if charge is None:
        raise HTTPException(404, "Rent charge not found.")
    if data.paid_amount_minor > charge.amount_minor:
        raise HTTPException(422, "Paid amount cannot exceed the charge.")
    if data.paid_amount_minor != charge.paid_amount_minor:
        charge.paid_amount_minor = data.paid_amount_minor
        charge.paid_at = datetime.now(timezone.utc) if charge.paid_amount_minor == charge.amount_minor else None
    db.commit()
    db.refresh(charge)
    return rent_view(charge)
