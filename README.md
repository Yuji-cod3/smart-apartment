# Smart Apartment Management System

FastAPI backend extended from `5daa050` ("Add device management and access control").
Existing apartments, rooms, devices, users, JWT login, and tenant/admin authorization are preserved.
No Packet Tracer or network architecture changes are included.

## Run locally

Use Python 3.12 or newer, from the repository root:

```sh
python -m venv .venv
# Activate .venv using your operating system's activation command.
python -m pip install -r backend/requirements.txt
```

Create a local `.env` (ignored by Git):

```dotenv
DATABASE_URL=sqlite:///./smart_apartment.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

Generate the secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Then initialize the database and create the initial administrator:

```sh
python -m alembic upgrade head
python -m backend.app.create_admin --email admin@example.com --full-name "Apartment Admin"
python -m uvicorn backend.app.main:app --reload
```

The administrator command prompts for a password twice and refuses to change an existing
account. Public registration still creates tenants only. Sign in at `POST /users/login`,
then use the returned bearer token in Swagger's **Authorize** control at `/docs`.
OpenAPI is available at `/openapi.json`. `/health` is liveness;
`/health/ready` checks database availability and required tables.

## Added API

All new business endpoints require the existing bearer authentication. Inactive users
are rejected even when they hold a previously issued token.

| Method | Path | Access / purpose |
| --- | --- | --- |
| GET | `/apartments/{apartment_id}/rooms/{room_id}/devices/{device_id}/state` | Admin or assigned tenant: read state |
| PUT | Same path ending in `/state` | Admin or assigned tenant: set `{"power":"on"}` or `{"power":"off"}` |
| GET | `/apartments/{apartment_id}/automations/` | Admin or assigned tenant: list rules |
| POST | `/apartments/{apartment_id}/automations/` | Admin: create rule |
| PUT | `/apartments/{apartment_id}/automations/{rule_id}` | Admin: replace a rule, including enable/disable |
| DELETE | `/apartments/{apartment_id}/automations/{rule_id}` | Admin: delete rule |
| POST | `/apartments/{apartment_id}/automations/evaluate` | Admin or assigned tenant: evaluate rules once |
| POST | `/rent/` | Admin: create monthly charge for assigned active tenant |
| GET | `/rent/` | Admin: all charges; tenant: own charges |
| GET | `/rent/{charge_id}` | Admin or the charged tenant |
| PUT | `/rent/{charge_id}/payment` | Admin: record/correct cumulative paid amount |
| GET | `/users/me` | Current account; no password hash |
| PATCH | `/users/{user_id}/status` | Admin: activate/deactivate a tenant |
| GET | `/users/{user_id}/tenant-status` | Admin or that tenant: assignment and balances |
| GET | `/dashboard/summary` | Role-scoped counts and rent balances |
| GET | `/health/ready` | Public: 200 ready or 503 unavailable |

### Device control

Supported power-control types are `light`, `fan`, `switch`, `smart_plug`, and
`air_conditioner`. Other existing types remain valid for device CRUD, but power
control returns 409 for unsupported types, offline devices, or disabled devices.
New and existing devices start with power `off`. Setting an unchanged state preserves
its update timestamp. Tenants cannot change device type, online status, or enabled status.

This is persisted **backend simulation state**, not a hardware command acknowledgement.
There is no MQTT, physical-device transport, or Packet Tracer modification in this milestone.

### Deterministic rules

Example create/replace payload:

```json
{
  "name": "Light follows switch",
  "source_device_id": 1,
  "source_power": "on",
  "target_device_id": 2,
  "target_power": "on",
  "is_enabled": true
}
```

Both devices must belong to the route's apartment and support power control. A source
cannot target itself. Each successful state-control request evaluates rules for that
source inside the same database transaction. Explicit `/evaluate` evaluates all rules
in the apartment. Rules use one snapshot, in ascending rule-ID order; the first eligible
matching rule for a target wins. There is no recursive chaining or scheduler. Repeating
an explicit evaluation takes a new snapshot and may therefore apply another step of a chain.

Evaluation returns per-rule outcomes: `applied`, `unchanged`, `not_matched`, `disabled`,
`unavailable`, or `conflict`. Unavailable targets are skipped. Deleting a device, room,
or apartment removes the associated rules. An admin changing a device type can make
existing rules unavailable until corrected.

### Rent and tenant status

Create a charge with:

```json
{
  "tenant_id": 2,
  "period": "2026-09",
  "due_date": "2026-09-30",
  "amount_minor": 75000,
  "currency": "XAF"
}
```

Amounts are nonnegative integer **minor units**, with a positive charge amount. For XAF,
75000 minor units is 75000 francs; for USD, 75000 minor units is 750 dollars. Currency is
an explicit three-uppercase-letter code; no conversion or currency-registry validation
is performed. Summaries keep different currencies separate.

One charge is allowed per tenant per `YYYY-MM` period. The apartment is captured when
the charge is created, so moving/unassigning a tenant does not change historical charges.
Apartments with rent history cannot be deleted (409). Rent is visible only to admins
and the charged tenant, including after the tenant moves out.

Payment payload: `{"paid_amount_minor":25000}`. This is the cumulative paid amount,
not an increment, so retries are idempotent. Admins can correct it up or down within
the charge amount. This is manual record keeping, not payment collection or an audited
accounting ledger. Concurrent corrections use the last committed value.

Statuses are computed on read using the UTC date: `paid` if the balance is zero;
`overdue` if a remaining balance's due date is before today; otherwise `partial` or
`unpaid`. A charge due today is not overdue. No background job is needed.

Assignment/removal synchronizes apartment occupancy and supports multiple tenants in
one apartment. Maintenance apartments reject new assignments. Inactive tenants cannot
receive new assignments or charges. Deactivation does not terminate a tenancy: admins
must explicitly remove the assignment. Self-deactivation and admin role changes are
not exposed by the tenant-status endpoint.

### Dashboard contract

`/dashboard/summary` returns apartment counts by status, tenant/active-tenant counts,
room and device counts, online/enabled/powered-on device counts, rule/enabled-rule counts,
and outstanding/overdue rent balances grouped by currency. Admins see all data;
tenants see their assigned apartment's resources and their own account and rent.
Unassigned tenants receive zero apartment/resource counts while retaining their own rent history.

`GET /rent/` supports `tenant_id`, `offset` (default 0), and `limit` (default 100,
maximum 200), ordered by due date descending then ID descending. Existing API list
conventions remain unchanged. The dashboard is served from the same FastAPI origin;
no cross-origin deployment policy or hardware transport is introduced.

## Database migrations

The previous initial revision contained no table creation. It now creates `apartments`
and `users` so a fresh `alembic upgrade head` works. Databases already stamped at that
revision or later do not rerun it.

New revisions:

1. `6a10c0de0001`: device `power` (default `off`), `state_updated_at`, power constraint.
2. `6a10c0de0002`: apartment automation rules, indexes, foreign keys, power constraints.
3. `6a10c0de0003`: rent charges, indexes, foreign keys, amount constraints, unique tenant/period.

SQLite foreign keys are enabled for runtime and migration connections. Back up an existing
database before upgrading. For a correctly populated and stamped database at
`4fb37f1d0a7f`, run `python -m alembic upgrade head`. If tables were previously created
manually and the database has no Alembic version, verify that its users, apartments,
rooms, and devices match the old schema before stamping `4fb37f1d0a7f`; do not blindly
stamp an unknown or partially migrated database. A database created using the old empty
initial migration alone needs its missing base tables repaired before upgrade.

Downgrading to `4fb37f1d0a7f` removes new state, rules, and rent records while retaining
the original tables and their records. Downgrading to `base` removes all application tables.

## Tests

Set `JWT_SECRET_KEY` to a test-only value before running:

```sh
python -m pytest -q
```

Tests use isolated SQLite databases and the original authentication dependencies.
New cases cover device control, rule determinism/conflicts and apartment isolation,
rent validation/ownership/payment retries, assignment occupancy, account deactivation,
dashboard scoping, migration upgrade/downgrade and schema parity, and an end-to-end
registration-to-rent-and-device-control scenario. Migration tests use temporary files;
they do not modify the application's configured database.

## Dashboard and isolated demo

Open `/dashboard` on the running server. Admins manage apartments, devices, routines,
rent records, and residents. Tenants see only their own apartment and rent history.

For a local demo with generated credentials and synthetic data:

```sh
python -m backend.app.demo --port 8765
```

Open `http://127.0.0.1:8765/dashboard`. The command prints the location of
`.demo/credentials.json`; use its admin or tenant email and password. This file,
the demo database, and secret are ignored by Git. Re-running preserves demo edits.
The demo binds to localhost. It is not a production deployment configuration.

### Rent countdown

After the first rent charge is paid in full, residents see a daily countdown on
Overview and Rent & payments. Admins see each resident's countdown in Residents.
The agreed monthly due date stays fixed: early or late payments do not shift it.
An outstanding recorded charge uses its actual due date, with older arrears first.
When all recorded charges are paid, the next date is an explicitly labeled estimate
one calendar month after the latest paid charge's due date (clamped to month end).
It stays overdue if missed; it does not silently advance or create a rent charge.
Unassigned/inactive residents get no estimated future charge. Partial first payments
do not activate it. Correcting all fully paid charges back to partial disables it.
Days use UTC, matching backend rent status, and open views update across midnight.

Countdown tests: `node frontend/tests/rent-countdown.test.mjs` (Node.js 22+).
