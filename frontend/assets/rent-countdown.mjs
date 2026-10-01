// Calendar days in UTC match the backend's rent status calculation.
export function rentCountdown(charges, tenant, now = new Date()) {
  const own = charges.filter(c => c.tenant_id === tenant.id);
  const paid = own.filter(c => c.amount_minor > 0 && c.paid_amount_minor === c.amount_minor);
  if (!paid.length) return {label: 'Starts after first full payment', due: null, days: null, projected: false};
  const outstanding = own.filter(c => c.paid_amount_minor < c.amount_minor)
    .sort((a, b) => a.due_date.localeCompare(b.due_date) || a.id - b.id);
  let due = outstanding[0]?.due_date;
  let projected = false;
  if (!due) {
    if (!tenant.apartment_id || !tenant.is_active) return {label: 'No upcoming charge', due: null, days: null, projected: false};
    // Use the agreed due date, not the date a late/early payment was recorded.
    const last = paid.sort((a, b) => b.due_date.localeCompare(a.due_date) || b.id - a.id)[0];
    const [year, month, day] = last.due_date.split('-').map(Number);
    const next = new Date(Date.UTC(year, month, 1));
    const monthEnd = new Date(Date.UTC(next.getUTCFullYear(), next.getUTCMonth() + 1, 0)).getUTCDate();
    next.setUTCDate(Math.min(day, monthEnd));
    due = next.toISOString().slice(0, 10);
    projected = true;
  }
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const days = Math.round((Date.parse(due + 'T00:00:00Z') - today) / 86400000);
  const label = days === 0 ? 'Due today' : days > 0 ? `${days} ${days === 1 ? 'day' : 'days'} until rent is due` : `${-days} ${days === -1 ? 'day' : 'days'} overdue`;
  return {label, due, days, projected};
}
