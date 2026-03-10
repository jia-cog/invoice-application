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
- **Database**: PostgreSQL (via Docker) with SQLAlchemy ORM
- **Environment**: Python virtual environment (.venv)

## Prerequisites

- Python 3.9+
- Node.js 16+
- Docker and Docker Compose

## Setup Instructions

### 1. Start the PostgreSQL Database

Start the PostgreSQL container using Docker Compose:

```bash
docker-compose up -d
```

This starts a PostgreSQL 15 instance with:
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `invoice_app`
- **User**: `invoice_user`
- **Password**: `invoice_pass`

To stop the database:
```bash
docker-compose down
```

To stop and remove all data:
```bash
docker-compose down -v
```

### 2. Backend Setup

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Configure environment variables (optional — defaults match docker-compose):
```bash
cp src/backend/.env.example src/backend/.env
# Edit src/backend/.env if your PostgreSQL settings differ
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

### 3. Frontend Setup

1. Install Node.js dependencies:
```bash
cd src/frontend
npm install
```

2. Start the React development server:
```bash
npm start
```

## Environment Variables

The backend reads the following environment variables (configured in `src/backend/.env`):

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://invoice_user:invoice_pass@localhost:5432/invoice_app` |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | `your-secret-key-change-in-production` |
| `SECRET_KEY` | Flask secret key | `your-secret-key-change-in-production` |

### Connection String Format

```
postgresql://<user>:<password>@<host>:<port>/<database>
```

To use SQLite instead (legacy/testing), set:
```
DATABASE_URL=sqlite:///invoice_app.db
```

## Project Structure

```
invoice-application/
├── docker-compose.yml        # PostgreSQL container configuration
├── requirements.txt          # Python backend dependencies
├── src/
│   ├── backend/
│   │   ├── app.py            # Flask application factory
│   │   ├── config.py         # Application configuration
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── init_db.py        # Database initialization script
│   │   ├── .env              # Local environment variables (not committed)
│   │   ├── routes/
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── invoices.py   # Invoice CRUD endpoints
│   │   │   └── reports.py    # Report generation endpoints
│   │   └── tests/
│   └── frontend/
│       ├── src/
│       ├── public/
│       └── package.json
└── README.md
```

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile
- `GET /api/invoices` - Get user invoices
- `POST /api/invoices` - Create new invoice
- `PUT /api/invoices/:id` - Update invoice
- `DELETE /api/invoices/:id` - Delete invoice
- `GET /api/reports` - Get reports
- `POST /api/reports/generate` - Generate report
- `GET /api/reports/dashboard` - Get dashboard data
- `DELETE /api/reports/:id` - Delete report

## Database Notes

### PostgreSQL-Specific Improvements

- **Monetary precision**: Financial columns (`subtotal`, `tax_amount`, `total_amount`, `unit_price`) use `NUMERIC(12,2)` instead of `FLOAT` for exact decimal arithmetic.
- **Native JSON**: Report data is stored using PostgreSQL's native `JSON` column type for better performance and querying capabilities.
- **Connection pooling**: SQLAlchemy is configured with connection pooling (`pool_size=10`, `max_overflow=20`) for better performance under load.

### Migration from SQLite

If migrating from an existing SQLite database, you will need to export your data and re-import it into PostgreSQL. The schema is created automatically when the application starts (`db.create_all()` in `app.py`).

## Usage

1. Register a new account or login
2. Create invoices with customer details and line items
3. View and manage your invoices
4. Generate reports from your invoice data
