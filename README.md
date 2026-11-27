# BookEase: Automated Bookkeeping Management System

**CSIT327 – Information Management 2**

BookEase is a Django-based bookkeeping system designed for small businesses. It uses PostgreSQL (including Supabase PostgreSQL) for persistent data storage and Django templates for its user interface.

## Project Development 2 – Core Feature

The core feature implemented in this increment is **Income and Expense Transaction Management (F-03)** from the approved Software Design Document (SDD).

A signed-in Business Owner can:

- Create, view, search, and filter income and expense transactions.
- Edit or delete their own transaction records.
- Assign owner-specific categories.
- Optionally link income transactions to customers and expense transactions to suppliers.
- View total income, total expenses, and net income on the owner dashboard.
- View transaction totals for a selected date range.
- Manage their own income/expense categories and customer/supplier contact records.

Transactions and their supporting categories and contacts are saved in PostgreSQL tables. Each transaction is linked to its owner through a ForeignKey to the custom User model.

Owner-facing views query only the signed-in owner's records. Administrators retain access to the administration dashboard and account/activity-log tools but cannot access owner bookkeeping pages or bookkeeping models through Django Admin.

### Important Business Rules

The system enforces the following rules:

- Transaction amounts must be positive.
- Transaction types must be valid INCOME or EXPENSE values.
- Transaction dates cannot be in the future.
- Categories must match the transaction type.
- Categories and contacts must belong to the same owner.
- Income transactions may be linked to customers.
- Expense transactions may be linked to suppliers.
- Category and contact names must be unique per owner, regardless of letter case.
- Referenced categories and contacts cannot be accidentally deleted.
- Important create, update, and delete actions are recorded in the activity log.

## Requirements

- Python 3.10 or newer
- PostgreSQL 13 or newer, or a Supabase PostgreSQL database
- Dependencies listed in `requirements.txt`

## Installation and Setup

### Windows PowerShell

1. Open PowerShell in the project folder containing `manage.py`.

2. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Upgrade pip:

   ```powershell
   python -m pip install --upgrade pip
   ```

5. Install the project dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Configure environment variables. Create a local `.env` file from the example if you do not already have one:

   ```powershell
   Copy-Item .env.example .env
   ```

   Open the `.env` file:

   ```powershell
   notepad .env
   ```

   Configure your own Django `SECRET_KEY`, database password, and other required settings.

   The `.env.example` file contains the sample Supabase Session Pooler configuration. Enter your own database credentials.

   **Never commit your private `.env` file to GitHub.**

7. Apply database migrations:

   ```powershell
   python manage.py migrate
   ```

8. Start the development server:

   ```powershell
   python manage.py runserver
   ```

9. Open the application in your browser:

   http://127.0.0.1:8000/

### macOS / Linux

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate it:

   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Create the environment file if it does not already exist:

   ```bash
   cp .env.example .env
   ```

5. Configure your `SECRET_KEY` and database credentials in `.env`.

6. Apply migrations:

   ```bash
   python manage.py migrate
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

Open http://127.0.0.1:8000/ in your browser.

## Roles and Main Routes

### Business Owner (OWNER)

Business Owners can access:

- `/dashboard/owner/` – Owner dashboard
- `/transactions/` – Income and expense transactions
- `/categories/` – Category management
- `/contacts/customers/` – Customer management
- `/contacts/suppliers/` – Supplier management
- `/profile/` – User profile

### Administrator (ADMIN)

Administrators can access:

- `/dashboard/admin/` – Administration dashboard
- User management
- System activity log

The `/dashboard/` route redirects authenticated accounts to their appropriate role dashboard.

Administrators are not allowed to access the Business Owner bookkeeping pages.

## Data and Business Logic

The project is organized into the following Django applications:

- `accounts` – Custom User model, authentication, registration, profile views, and activity logs.
- `bookkeeping` – Category, Customer, Supplier, and Transaction models, forms, owner-only views, and templates.
- `config` – Django project settings, URL configuration, and custom error handlers.
- `templates` – Application templates and custom error pages.
- `static` – Static CSS and other front-end assets.

### Database Migrations

- `bookkeeping/migrations/0001_initial.py` creates the bookkeeping tables and initial PostgreSQL constraints, including the transaction/category composite foreign key for category/type matching.
- `accounts/migrations/0002_pd3_hardening.py` and `bookkeeping/migrations/0002_pd3_hardening.py` apply PD3 relationship-protection, case-insensitive uniqueness, amount-validation, and query-index changes.

The `.env` file is ignored by Git. Database passwords and Django secret keys must never be committed.

## Project Development 3 – Hardening of Core Features

No new user-facing features are introduced in PD3. This increment focuses on making the existing account and transaction workflows reliable, secure, and properly tested.

### 1. Validation and Error Handling

- Server-side validation is implemented for core feature forms.
- Positive transaction amounts are enforced.
- Future transaction dates are rejected.
- Category/type matching and owner relationships are validated.
- Success and error messages provide feedback to users.
- Custom 403, 404, and 500 error pages are configured.
- Invalid object lookups use appropriate 404 handling.
- Debug details are not displayed in the public error templates.

### 2. Security and Access Control

- Owner-role checks are enforced inside views.
- Bookkeeping querysets and detail lookups are scoped to the signed-in owner.
- Users cannot access another owner's transaction records by changing the ID in the URL.
- CSRF tokens are included in POST forms.
- Delete endpoints accept POST requests only.
- Django ORM is used instead of raw SQL constructed from user input.
- User-provided input is not rendered using unsafe template output.
- `SECRET_KEY` and `DEBUG` are controlled through environment variables.

### 3. Data Integrity and Database

- Model constraints and validators enforce valid data.
- Case-insensitive duplicate category and contact names are prevented through database constraints and form validation.
- Related owner, category, and contact records use appropriate `PROTECT` behavior.
- Multi-step database operations and activity logging use `transaction.atomic()`.
- Successful POST operations redirect using the Post/Redirect/Get pattern.
- Related objects use `select_related()` and `prefetch_related()` where needed.
- Delete actions require confirmation before submission.

### 4. Automated Testing

The project contains automated Django tests in:

- `bookkeeping/tests.py`
- `accounts/tests.py`

The test suite covers:

- Valid transaction creation.
- Invalid transaction amounts.
- Login requirements.
- Role-based access restrictions.
- Cross-owner transaction access denial.
- CSRF protection.
- POST-only delete restrictions.
- Missing transaction IDs.
- Duplicate category and contact names.
- Transaction create, update, and delete operations.
- Account registration and authentication.
- User profiles and password changes.
- Administrator access and database constraints.

## How to Run the Automated Tests

Run the following commands whenever you want to execute the complete automated test suite.

### Windows PowerShell

1. Open PowerShell in the BookEase project directory (the folder containing `manage.py`).

2. Activate the virtual environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Execute all Django tests:

   ```powershell
   python manage.py test
   ```

### macOS / Linux

1. Open a terminal in the BookEase project directory.

2. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

3. Execute all Django tests:

   ```bash
   python manage.py test
   ```

### Expected Test Output

When all tests pass, Django displays output similar to:

```text
Found 82 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
..................................................................................
----------------------------------------------------------------------
Ran 82 tests

OK
Destroying test database for alias 'default'...
```

### Latest Verified Test Results

The PD3 automated test suite was executed locally with the following results:

| Test Result | Status |
|---|---|
| Total tests discovered | 82 |
| Tests passed | 82 |
| Tests failed | 0 |
| Django system checks | No issues |
| Overall result | PASSED |

Django automatically creates an isolated test database, executes the tests, and destroys the test database afterward.

The test configuration uses an isolated SQLite test database. This prevents the automated test run from modifying the live Supabase database. Normal commands such as `migrate` and `runserver` continue to use the PostgreSQL/Supabase settings configured in `.env`.

## Environment and Security Configuration

The source ZIP and public GitHub repository intentionally exclude the private `.env` file.

The repository includes `.env.example` as a reference for environment configuration.

Security requirements:

- Keep `.env` in `.gitignore`.
- Never commit database passwords.
- Never commit Django secret keys.
- Generate a new `SECRET_KEY` for your local environment.
- Keep `DEBUG=False` for non-debug deployments.
- Configure `ALLOWED_HOSTS` for the intended deployment.
- For HTTPS deployments, configure:

  ```env
  SESSION_COOKIE_SECURE=True
  CSRF_COOKIE_SECURE=True
  SECURE_SSL_REDIRECT=True
  ```

The supplied `.env.example` is configured for local HTTP development.

## Current Increment Boundary

Receipt upload/linking and detailed financial report generation are not included in this core-feature increment. These items remain deferred to a future increment.

The existing standard features from Project Development 1 remain part of the system:

- Account Registration
- Login and Logout
- Role-Based User Dashboard
- User Profile

## Project Repository

**System:** BookEase – Automated Bookkeeping Management System

**Core Feature:** Income and Expense Transaction Management (F-03)

**GitHub Repository:**  
https://github.com/LanceAngeloReusora/BookEase-Reusora-LanceAngelo-G5

**Project Development:** 3 – Hardening of Core Features
