# BookEase: Automated Bookkeeping Management System

CSIT327 Information Management 2 – Project Development 1 (Account Feature)

Full-stack Django (templates) + PostgreSQL. Built from the project's Software Design Document: the `users` and `activity_logs` tables, business rules BR-01 to BR-05 and BR-22/BR-23.

## Setup

Requires Python 3.10+ and a PostgreSQL database (local or Supabase).

```bash
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

copy .env.example .env         # macOS/Linux: cp .env.example .env
# edit .env: SECRET_KEY and your database credentials

python manage.py migrate
python manage.py createsuperuser   # creates an ADMIN account
python manage.py runserver
```

Open http://127.0.0.1:8000/. Business owners sign up from the Register page; administrators are created with `createsuperuser`.

**Local PostgreSQL:** create an empty database first (`CREATE DATABASE bookease;`).
**Supabase:** use the values from Project Settings > Database in `.env` and set `DB_SSLMODE=require`.

Run the tests (they run on PostgreSQL): `python manage.py test accounts`

## Account feature

| Requirement | Where |
|---|---|
| Registration with validation, hashed passwords, messages | `accounts/forms.py` (`RegistrationForm`), `views.register` |
| Login / logout, invalid-credential error, session ends on logout | `views.BookEaseLoginView`, `views.logout_view` |
| Protected pages (`login_required`) | `accounts/decorators.py` |
| Role-based dashboards (OWNER, ADMIN) | `views.owner_dashboard`, `views.admin_dashboard` |
| Other role's URL is blocked (403) | `role_required` decorator |
| View / edit own profile, change password | `views.profile`, `profile_edit`, `password_change` |
| Admin: deactivate/reactivate users, view activity log | `views.admin_users`, `admin_activity` |

## Roles

- **OWNER (Business Owner):** `/dashboard/owner/`
- **ADMIN (Administrator):** `/dashboard/admin/`, user management, system activity log

`/dashboard/` redirects each user to the dashboard for their role.

## Notes

- Database tables and columns follow the SDD (`users`, `activity_logs`), including the CHECK/UNIQUE constraints.
- Accounts are deactivated, never deleted (BR-04). A deactivated user cannot log in, and an existing session stops working.
- Transactions, categories, receipts, customers, suppliers and reports are later phases; the owner dashboard shows them as "Coming soon".
