# BookEase: Automated Bookkeeping Management System

CSIT327 – Information Management 2. BookEase is a Django bookkeeping system for small businesses. It uses PostgreSQL (including Supabase PostgreSQL) for persistent data and Django templates for the user interface.

## Project Development 2 core feature

The core feature implemented in this increment is **income and expense transaction management (F-03)** from the approved SDD.

A signed-in Business Owner can:

- Create, view, search, and filter income and expense transactions.
- Edit or delete their own transaction records.
- Assign an owner-specific category and optionally link an income transaction to a customer or an expense transaction to a supplier.
- View total income, total expenses, and net income on the owner dashboard, including totals for a selected date range.
- Manage their own income/expense categories and customer/supplier contact records.

Transactions and their supporting categories/contacts are saved in PostgreSQL tables. A transaction is linked to its owner through a `ForeignKey` to the custom User model. Owner-facing views query only the signed-in owner's records. Administrators retain the administration dashboard and cannot access owner bookkeeping pages.

Important SDD rules enforced by the feature include positive amounts, valid INCOME/EXPENSE types, category/type matching, no future transaction dates, same-owner category/contact relationships, income/customer and expense/supplier linking rules, unique owner-scoped category/contact names, and prevention of deleting categories or contacts referenced by transactions. Important create/update/delete actions are added to the activity log.

## Requirements

- Python 3.10 or newer
- PostgreSQL 13 or newer, or a Supabase PostgreSQL database
- Dependencies listed in `requirements.txt`

## Setup

### Windows PowerShell

1. Open a terminal in the folder containing `manage.py`.
2. Create and activate the virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies inside that environment:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Configure the environment. The private project bundle includes the `.env` file supplied with the original BookEase project, so you normally do not need to recreate it. If you obtained the project from public GitHub (where `.env` is intentionally not committed), create it from the example:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   The supplied Supabase Session Pooler settings are already filled in in `.env.example` (`DB_HOST`, `DB_USER`, `DB_NAME`, port `5432`, and SSL mode `require`). Enter your own Supabase database password and a new Django `SECRET_KEY` before running the app.

5. Apply database migrations and start the server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

Open `http://127.0.0.1:8000/`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # only if you do not already have your private .env
# Fill in SECRET_KEY and DB_PASSWORD in .env
python manage.py migrate
python manage.py runserver
```

**Security:** `.env` is listed in `.gitignore` and must never be committed. It contains private credentials. The public repository should contain `.env.example` only.

## Roles and main routes

- **OWNER (Business Owner):** `/dashboard/owner/`, `/transactions/`, `/categories/`, `/contacts/customers/`, `/contacts/suppliers/`, and `/profile/`.
- **ADMIN (Administrator):** `/dashboard/admin/`, user management, and the system activity log.

`/dashboard/` redirects each authenticated account to its role dashboard. An Administrator is not allowed to open the Owner bookkeeping pages.

## Data and business logic

- `accounts` contains the custom `User` model, authentication/profile views, and `activity_logs`.
- `bookkeeping` contains `Category`, `Customer`, `Supplier`, and `Transaction` models, forms, owner-only views, and templates.
- `bookkeeping/migrations/0001_initial.py` creates the bookkeeping tables and PostgreSQL constraints, including the transaction/category composite foreign key for category/type matching.
- `.env` is ignored by Git. Do not commit database passwords or Django secret keys.

## Tests

Run the Django test suite against the configured PostgreSQL database:

```bash
python manage.py test
```

The account tests cover registration, login/logout, role dashboards, profile management, admin access, and account constraints. The bookkeeping tests cover transaction CRUD, validation, ownership isolation, role access, category/contact relationships, deletion restrictions, activity logging, filters, and dashboard totals.

## Current increment boundary

Receipt upload/linking and detailed financial report generation are not included in this core-feature increment. The existing registration, login/logout, role dashboards, and profile features remain part of the project.
