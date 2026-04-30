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

### Required Environment Variables (Production)

The application requires the following environment variables to be set before starting. It will **refuse to start** if any are missing.

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | Secret key used to sign and verify JWT access tokens. Must be a strong, unique value. |
| `SECRET_KEY` | Flask secret key used for session signing and CSRF protection. Must be a strong, unique value. |

Generate secure values using Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Example setup for production:

```bash
export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

> **Warning:** Never commit secret keys to version control or use the same keys across environments.

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

3. Set required environment variables (see [Required Environment Variables](#required-environment-variables-production) above):
```bash
export JWT_SECRET_KEY="your-generated-secret"
export SECRET_KEY="your-generated-secret"
```

4. Initialize the database:
```bash
cd src/backend
python3 init_db.py
```

5. Run the Flask server:
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
