# Invoice Application

A full-stack invoicing application built with React.js frontend and Flask backend.

## Features

- User account creation and authentication
- Multi-tenant data isolation: every invoice and report belongs to a tenant, and access tokens are scoped to one tenant at a time
- Invoice creation and management
- Report generation from invoices
- Responsive design

## Tech Stack

- **Frontend**: React.js with responsive design
- **Backend**: Flask (Python)
- **Database**: PostgreSQL (schema managed by Alembic via Flask-Migrate)
- **Environment**: Python virtual environment (.venv)

## Setup Instructions

### Backend Setup

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Point the app at a PostgreSQL database (defaults to
   `postgresql+psycopg2://invoice:invoice@localhost:5432/invoice_app`):
```bash
export DATABASE_URL=postgresql+psycopg2://invoice:invoice@localhost:5432/invoice_app
```

4. Apply migrations:
```bash
cd src/backend
python3 init_db.py   # equivalent to: FLASK_APP=app.py flask db upgrade
```

5. Run the Flask server:
```bash
python3 app.py
```

### Database Migrations

Schema changes are managed with Flask-Migrate from `src/backend`:

```bash
export FLASK_APP=app.py
flask db migrate -m "describe the change"   # generate a revision from model changes
flask db upgrade                            # apply pending revisions
flask db downgrade                          # roll back one revision
```

### Frontend Setup

1. Install Node.js dependencies:
```bash
cd src/frontend
npm install
```

2. Start the React development server:
```bash
npm start
```

## Project Structure

```
invoice-application/
├── src/
│   ├── backend/
│   │   ├── app.py
│   │   ├── models.py
│   │   ├── tenancy.py
│   │   ├── migrations/
│   │   └── routes/
│   └── frontend/
│       ├── src/
│       ├── public/
│       └── package.json
├── requirements.txt
└── README.md
```

## API Endpoints

- `POST /api/auth/register` - Register new user, creating a tenant owned by them
- `POST /api/auth/login` - User login (optional `tenant_slug` selects the tenant)
- `GET /api/auth/tenants` - List the caller's tenant memberships
- `POST /api/auth/tenants/switch` - Get a token scoped to another tenant
- `GET /api/invoices` - Get the tenant's invoices
- `POST /api/invoices` - Create new invoice
- `GET /api/reports` - Generate reports

## Multi-tenancy

All tenants share one schema and every business row carries a `tenant_id`. Requests are scoped by
the `tenant_id` claim in the access token, which `tenancy.tenant_required` re-validates against the
caller's memberships on every request, so revoking a membership takes effect immediately. Invoice
numbers are unique per tenant rather than globally. Registration provisions a tenant for the new
user; additional memberships (a user in several tenants) are granted by inserting rows in
`tenant_membership`, and clients move between them with `POST /api/auth/tenants/switch`.

## Usage

1. Register a new account or login
2. Create invoices with customer details and line items
3. View and manage your invoices
4. Generate reports from your invoice data
