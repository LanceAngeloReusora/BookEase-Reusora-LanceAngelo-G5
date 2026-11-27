# PD3 Git workflow (same BookEase repository)

Keep using the existing public repository. Do not replace its `.git` directory. Copy the updated source files into your existing clone, but keep your private `.env` and `.venv` files.

The suggested three work branches divide the changes into reviewable increments. Create each branch from the latest `develop`, push it, open a PR into `develop`, and merge that PR before starting the next branch.

## 1. Fix error pages and admin exposure

```powershell
git fetch origin
git switch develop
git pull origin develop
git switch -c fix/pd2-outstanding-issues
git add .env.example config/error_views.py config/urls.py bookkeeping/admin.py templates/404.html templates/500.html templates/accounts/_field.html
git commit -m "Add generic error pages and restrict admin data access"
git push -u origin fix/pd2-outstanding-issues
```

Create a PR from `fix/pd2-outstanding-issues` into `develop` and merge it.

## 2. Harden data integrity and access

After PR 1 has merged:

```powershell
git switch develop
git pull origin develop
git switch -c hardening/access-control
git add accounts/models.py accounts/views.py accounts/migrations/0002_pd3_hardening.py bookkeeping/models.py bookkeeping/views.py bookkeeping/migrations/0002_pd3_hardening.py templates/bookkeeping/category_list.html
git commit -m "Harden owner access and database integrity"
git push -u origin hardening/access-control
```

Create a PR from `hardening/access-control` into `develop` and merge it.

## 3. Add automated regression tests

After PR 2 has merged:

```powershell
git switch develop
git pull origin develop
git switch -c test/core-feature-hardening
git add accounts/tests.py bookkeeping/tests.py config/settings.py README.md docs/PD3-Git-Workflow.md
git commit -m "Add hardening tests and document test execution"
git push -u origin test/core-feature-hardening
```

Create a PR from `test/core-feature-hardening` into `develop` and merge it.

## Final release PR

Once all three work PRs are merged, open a PR from `develop` into `main`, review it, and merge it. Keep the work branches after merging.

## Safety reminders

- Never stage `.env`, `.venv`, database dumps, or local SQLite files. Use exact file paths with `git add`; avoid `git add .` when unsure.
- The actual PD3 report PDF must be placed in `docs/` as a separate step once the official PD3 report template has been filled.
- Run `python manage.py test` before opening the release PR, then `python manage.py migrate` against the configured Supabase project and smoke-test login, owner CRUD, role restrictions, and error pages.
