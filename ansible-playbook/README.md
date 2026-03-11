# Invoice Application - Ansible Deployment Playbook

This Ansible playbook automates the deployment of the full-stack Invoice Application (Flask backend + React frontend) to a production server.

## Architecture

```
Client Browser
      │
      ▼
   Nginx (port 443/80)
   ├── /api/*  ──▶  Gunicorn/Flask (port 5001)
   │                      │
   │                      ▼
   │                 SQLite Database
   │
   └── /*  ──▶  React Static Files (build/)
```

## Directory Structure

```
ansible-playbook/
├── site.yml                           # Main playbook entry point
├── inventory/
│   └── production.ini                 # Production server inventory
├── group_vars/
│   └── production.yml                 # Production environment configuration
└── roles/
    ├── system-deps/                   # Python3, Node.js, pip, npm, Nginx
    ├── invoice-app-backend/           # Flask app, venv, gunicorn, systemd
    ├── invoice-app-frontend/          # React build, static file preparation
    ├── database/                      # SQLite setup, safe schema init, backups
    ├── webserver/                     # Nginx reverse proxy + static serving
    └── security/                      # UFW firewall, SSL/TLS, CORS lockdown
```

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ (Debian-based)
- **SSH access**: Key-based SSH access to the target server
- **Ansible collections**: `community.general` (for UFW and npm modules)

Install required collections:
```bash
ansible-galaxy collection install community.general
```

## Quick Start

### 1. Configure Inventory

Edit `inventory/production.ini` and add your server:

```ini
[invoice_servers]
invoice-prod ansible_host=YOUR_SERVER_IP ansible_user=deploy
```

### 2. Configure Secrets

Create an Ansible Vault file for secrets:

```bash
ansible-vault create group_vars/vault.yml
```

Add the following variables:

```yaml
vault_jwt_secret_key: "your-secure-random-jwt-secret-here"
vault_flask_secret_key: "your-secure-random-flask-secret-here"
```

Generate secure secrets:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Update Production Configuration

Edit `group_vars/production.yml` and set:
- `frontend_domain` to your actual domain name
- Any other environment-specific values

### 4. Run the Playbook

**First-time deployment** (initializes the database):
```bash
ansible-playbook -i inventory/production.ini site.yml \
  -e "first_time_provision=true" \
  --ask-vault-pass
```

**Subsequent deployments** (preserves existing database):
```bash
ansible-playbook -i inventory/production.ini site.yml \
  --ask-vault-pass
```

**Deploy specific roles only**:
```bash
# Backend only
ansible-playbook -i inventory/production.ini site.yml --tags backend

# Frontend only
ansible-playbook -i inventory/production.ini site.yml --tags frontend

# Security updates only
ansible-playbook -i inventory/production.ini site.yml --tags security
```

## Roles

### system-deps
Installs all system-level packages: Python3, pip, Node.js (v18), npm, Nginx, SQLite, build tools, and git.

### invoice-app-backend
- Clones the application repository
- Creates a Python virtual environment at `.venv`
- Installs Python dependencies from `requirements.txt`
- Deploys a production WSGI entry point using Gunicorn (not Flask's debug server)
- Deploys production configuration that overrides CORS to restrict origins
- Configures environment variables (`DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY`)
- Creates and manages a systemd service for the backend

### database
- Creates the SQLite database directory with proper permissions
- **Safe initialization**: Uses `db.create_all()` (not the destructive `init_db.py` which calls `db.drop_all()`)
- Only initializes schema on first-time provisioning or when the database file doesn't exist
- Sets up daily automated backups with 7-day retention via cron

### invoice-app-frontend
- Installs npm dependencies from `src/frontend/package.json`
- Sets `REACT_APP_API_URL` at build time to the production backend URL
- Runs `npm run build` to generate the production bundle
- Verifies the build output exists

### webserver
- Configures Nginx as a reverse proxy and static file server
- Proxies `/api/*` requests to the Flask backend on port 5001
- Serves React static files from the build directory
- Handles SPA routing with `try_files` fallback to `index.html`
- Adds cache headers for static assets
- Includes security headers (X-Frame-Options, X-Content-Type-Options, etc.)

### security
- Configures UFW firewall (allows SSH, HTTP, HTTPS; denies everything else)
- Generates a self-signed SSL certificate for initial setup
- Installs certbot for Let's Encrypt certificate provisioning
- Sets up automatic certificate renewal via cron
- Enforces restrictive file permissions on secrets and database
- CORS is locked down to the production frontend domain only (no wildcards)

## Idempotency

This playbook is designed to be run multiple times safely:

- **Database**: Schema initialization is guarded by `first_time_provision` flag and database file existence check. It uses `db.create_all()` which only creates tables that don't exist.
- **SSL certificates**: Self-signed certs are only generated if no certificate exists. Let's Encrypt renewal is handled automatically.
- **Service management**: Systemd services are only restarted when configuration changes.
- **Git clone**: The repository is updated (not re-cloned) on subsequent runs.

## Security Considerations

1. **Secrets**: JWT and Flask secret keys should be stored in Ansible Vault, not in plain text.
2. **CORS**: Production configuration restricts CORS to only the frontend domain (removes the `*` wildcard from development).
3. **Database**: The destructive `init_db.py` script is never executed; safe `db.create_all()` is used instead.
4. **File permissions**: The `.env` file is mode 0600; the database file is mode 0640.
5. **Firewall**: UFW blocks all incoming traffic except SSH (22), HTTP (80), and HTTPS (443).
6. **Systemd hardening**: The backend service runs with `NoNewPrivileges`, `PrivateTmp`, and `ProtectSystem=strict`.

## Assumptions

- Target server runs Ubuntu 20.04 or later (Debian-based)
- SSH key-based authentication is configured for the deploy user
- The deploy user has sudo/become privileges
- DNS is configured to point `frontend_domain` to the server's IP address
- The GitHub repository is publicly accessible (or deploy keys are configured)
