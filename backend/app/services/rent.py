from datetime import datetime, timezone

from backend.app.models.rent import RentCharge


def rent_view(charge: RentCharge) -> dict:
    balance = charge.amount_minor - charge.paid_amount_minor
    today = datetime.now(timezone.utc).date()
    if balance == 0:
        status = "paid"
    elif charge.due_date < today:
        status = "overdue"
    elif charge.paid_amount_minor:
        status = "partial"
    else:
        status = "unpaid"
    return {
        "id": charge.id, "tenant_id": charge.tenant_id,
        "apartment_id": charge.apartment_id, "period": charge.period,
        "due_date": charge.due_date, "amount_minor": charge.amount_minor,
        "currency": charge.currency, "paid_amount_minor": charge.paid_amount_minor,
        "balance_minor": balance, "paid_at": charge.paid_at, "status": status,
    }


def rent_balances(charges) -> list[dict]:
    totals = {}
    for charge in charges:
        view = rent_view(charge)
        total = totals.setdefault(charge.currency, {"currency": charge.currency, "outstanding_minor": 0, "overdue_minor": 0})
        total["outstanding_minor"] += view["balance_minor"]
        if view["status"] == "overdue":
            total["overdue_minor"] += view["balance_minor"]
    return [totals[currency] for currency in sorted(totals)]
