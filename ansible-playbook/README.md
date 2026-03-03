# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the full-stack Invoice Application to production servers.

## Architecture

- **Backend**: Flask (Python) served by Gunicorn on port 5001, managed by systemd
- **Frontend**: React.js production build served as static files by Nginx
- **Database**: SQLite (file-based)
- **Reverse Proxy**: Nginx handles SSL termination, static files, and API proxying
- **Authentication**: JWT with 24-hour expiration

## Directory Structure

```
ansible-playbook/
├── site.yml                          # Main playbook entry point
├── inventories/
│   └── production.ini                # Production inventory (add your servers)
├── group_vars/
│   └── production.yml                # Production environment configuration
└── roles/
    ├── system-deps/                  # Python3, Node.js, Nginx, system packages
    ├── database/                     # SQLite setup with safe initialization
    ├── invoice-app-backend/          # Flask app, venv, Gunicorn, systemd service
    ├── invoice-app-frontend/         # React build with production API URL
    ├── webserver/                    # Nginx configuration and site setup
    └── security/                     # Firewall, SSL, CORS hardening, secrets
```

## Prerequisites

- **Target servers**: Ubuntu 20.04+ (Debian-based)
- **Ansible**: 2.12+ on the control node
- **SSH access**: Key-based authentication to target servers
- **Python 3**: On both control node and target servers

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` and add your target server(s):

```ini
[invoice_servers]
invoice-prod-01 ansible_host=YOUR_SERVER_IP

[invoice_servers:vars]
ansible_user=ubuntu
ansible_python_interpreter=/usr/bin/python3
```

### 2. Configure Secrets

**Important**: Update the secrets in `group_vars/production.yml` before deploying.

For production, use Ansible Vault to encrypt sensitive values:

```bash
# Create an encrypted vault file for secrets
ansible-vault create group_vars/vault.yml
```

Add the following to `vault.yml`:

```yaml
vault_jwt_secret_key: "your-secure-random-jwt-secret"
vault_flask_secret_key: "your-secure-random-flask-secret"
```

Then reference vault variables in `production.yml` (already configured).

### 3. Run the Playbook

```bash
# Full deployment
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass

# Deploy specific roles using tags
ansible-playbook -i inventories/production.ini site.yml --tags backend
ansible-playbook -i inventories/production.ini site.yml --tags frontend
ansible-playbook -i inventories/production.ini site.yml --tags webserver

# Dry run (check mode)
ansible-playbook -i inventories/production.ini site.yml --check --diff
```

## Roles

### system-deps
Installs all system-level packages: Python3, pip, venv, Node.js (v18), npm, Nginx, and build tools. Creates the application user and group.

### database
Manages SQLite database initialization with **safety guards**. The application's `init_db.py` calls `db.drop_all()` which would destroy all data. This role uses a marker file (`.db_initialized`) to ensure schema creation only runs on first-time provisioning, never on redeployment.

### invoice-app-backend
Clones the repository, creates a Python virtual environment, installs dependencies (flask, flask-sqlalchemy, flask-jwt-extended, flask-cors, werkzeug, gunicorn), deploys environment configuration, and sets up a systemd service running Gunicorn instead of Flask's development server.

### invoice-app-frontend
Installs npm dependencies and builds the React application with `REACT_APP_API_URL` set to the production backend URL at build time. The build output is served as static files by Nginx.

### webserver
Configures Nginx as a reverse proxy:
- Serves React static files from the build directory
- Proxies `/api/` requests to the Gunicorn backend
- Handles SPA routing (fallback to `index.html`)
- Enables gzip compression and security headers
- Optional SSL/TLS termination with HTTP-to-HTTPS redirect

### security
- **Firewall**: UFW configured to allow only SSH, HTTP, and HTTPS
- **SSL**: Generates self-signed certificates if none are provided (replace with real certs for production)
- **CORS**: Deploys a production CORS configuration restricting origins to the frontend domain only (replaces the development wildcard `*`)
- **SSH hardening**: Disables root login and password authentication
- **File permissions**: Restricts access to sensitive files (.env, database)

## Idempotency

The playbook is designed to be run multiple times safely:
- Database initialization only runs once (marker file guard)
- Configuration files are templated and only trigger restarts when changed
- Services are managed declaratively via systemd
- Package installations use `state: present` (not `latest`)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database URI | `sqlite:///instance/invoice_app.db` |
| `JWT_SECRET_KEY` | Secret for signing JWTs | Must be set via vault |
| `SECRET_KEY` | Flask session secret | Must be set via vault |
| `FLASK_ENV` | Flask environment | `production` |
| `REACT_APP_API_URL` | Backend API URL (build-time) | `https://<domain>/api` |

## SSL Certificates

By default, the security role generates a self-signed certificate. For production:

1. Obtain certificates from a CA (e.g., Let's Encrypt)
2. Place them at the paths configured in `production.yml`
3. Or override `ssl_certificate_path` and `ssl_certificate_key_path`

## Troubleshooting

```bash
# Check backend service status
sudo systemctl status invoice-backend

# View backend logs
sudo journalctl -u invoice-backend -f

# Check Nginx status
sudo systemctl status nginx

# Test Nginx configuration
sudo nginx -t

# Check health endpoint
curl http://localhost:5001/api/health
```
