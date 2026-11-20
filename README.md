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

1. Clone or download the repository and open a terminal in the project folder.
2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set your Django secret key and PostgreSQL credentials:

   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   # macOS/Linux
   cp .env.example .env
   ```

   **For Supabase (recommended):**

   1. Open your Supabase project and click **Connect**.
   2. Choose **Session pooler** and copy its host and username exactly. This mode is suitable for local networks that only support IPv4.
   3. In `.env`, set `DB_NAME=postgres`, `DB_USER` to the session-pooler username (usually `postgres.<PROJECT-REF>`), `DB_HOST` to the pooler host, `DB_PORT=5432`, your database password, and `DB_SSLMODE=require`.

   Supabase direct connections use host `db.<PROJECT-REF>.supabase.co`, username `postgres`, and port `5432`; they require IPv6 unless your project has the IPv4 add-on. Use the exact connection details shown by Supabase rather than guessing the pooler hostname or username.

   **For a local PostgreSQL database instead:** set `DB_NAME=bookease`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost`, and `DB_PORT=5432`.

5. Apply the migrations and create an administrator account:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

Open `http://127.0.0.1:8000/`. Business Owners can register from the Register page. Administrators are created with `createsuperuser`.

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
