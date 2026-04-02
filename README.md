# Invoice Application

A full-stack invoicing application built with React.js frontend and Flask backend.

## Features

- User account creation and authentication
- Invoice creation and management
- Report generation from invoices
- Responsive design

## Tech Stack

- **Frontend**: React.js with responsive design
- **Backend**: Flask (Python)
- **Database**: SQLite
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

3. Initialize the database:
```bash
cd src/backend
python3 init_db.py
```

4. Run the Flask server:
```bash
python3 app.py
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

## Required Environment Variables (Production)

The following environment variables **must** be set before starting the application. The server will refuse to start if they are missing.

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | Secret key used to sign and verify JWT access tokens. Must be a strong, unique value. |
| `SECRET_KEY` | Flask session secret key. Must be a strong, unique value. |

### Generating Secure Secrets

Use Python's `secrets` module to generate cryptographically secure values:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run this command **twice** to produce separate values for `JWT_SECRET_KEY` and `SECRET_KEY`. Then export them in your environment (or add them to your deployment configuration):

```bash
export JWT_SECRET_KEY="<generated-value>"
export SECRET_KEY="<generated-value>"
```

### Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///invoice_app.db` | Database connection URI |
| `API_BASE_URL` | `http://localhost:5001/api` | Base URL used by the bootstrap script |
| `ENV` / `FLASK_ENV` | *(empty)* | Set to `production` to enable production safeguards (e.g., blocks the bootstrap script) |

## Project Structure

```
invoice-application/
├── src/
│   ├── backend/
│   │   ├── app.py
│   │   ├── models.py
│   │   ├── routes/
│   │   └── database.db
│   └── frontend/
│       ├── src/
│       ├── public/
│       └── package.json
├── requirements.txt
└── README.md
```

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/invoices` - Get user invoices
- `POST /api/invoices` - Create new invoice
- `GET /api/reports` - Generate reports

## Usage

1. Register a new account or login
2. Create invoices with customer details and line items
3. View and manage your invoices
4. Generate reports from your invoice data
