# AI-Enabled Question Paper Retrieval System (Django + PostgreSQL)

Roles (login with **email + password**):
- **Admin** - manages users (add/edit/disable/delete), all question papers, and sees the analytics dashboard (uploads, downloads, views, activity log).
- **Faculty** - uploads semester / internal question papers (PDF + metadata), manages own uploads.
- **Student** - searches (keyword + filters), views and downloads PDFs.

Every login, upload, view, download and delete is logged for the admin. Duplicate PDFs are rejected (SHA-256). PDFs are stored in `media/` and are only reachable through login-protected URLs. "Related papers" on each paper page are suggested by matching subject code/name.

## Run
```
python -m venv venv && venv\Scripts\activate     (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_demo          # demo logins below
python manage.py runserver
```
Open http://127.0.0.1:8000/

| Role | Email | Password |
|---|---|---|
| Admin | admin@srit.ac.in | admin123 |
| Faculty | faculty@srit.ac.in | faculty123 |
| Student | student@srit.ac.in | student123 |

Change these passwords (Admin > Users > Edit) before real use.

## PostgreSQL
Without settings it uses SQLite so you can test immediately. For PostgreSQL create a database, then set environment variables before `migrate`:
```
set DB_NAME=qpdb  & set DB_USER=postgres & set DB_PASSWORD=yourpass & set DB_HOST=localhost
```
(Linux/Mac: use `export`.)

## Structure
`config/` settings + urls, `core/models.py` (User, Paper, ActivityLog), `core/views.py`, `core/forms.py`, `core/templates/core/` (Bootstrap 5 pages).
