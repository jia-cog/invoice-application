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

### Required Environment Variables (Production)

The application requires the following environment variables to be set before it will
start. This prevents the use of weak, hardcoded fallback secrets in production.

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` | Signing key for JSON Web Tokens (JWT) |
| `SECRET_KEY` | Flask session / CSRF secret key |

Generate strong, unique values with Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set them in your environment before running the server:

```bash
export JWT_SECRET_KEY="<generated-value>"
export SECRET_KEY="<generated-value>"
```

> **Note:** The bootstrap sample-data script (`src/backend/bootstrap/bootstrap_sample_data.py`)
> is intended for **development only** and will refuse to run when `ENV=production`.

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
