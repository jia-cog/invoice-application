# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the full-stack Invoice Application to production. Manages the Flask backend, React frontend, Nginx reverse proxy, SQLite database, and security hardening.

## Architecture

```
                    ┌─────────────┐
                    │   Clients   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │
                    │  (port 443) │
                    └──┬──────┬───┘
                       │      │
              /api/*   │      │  /*
                       │      │
               ┌───────▼──┐ ┌─▼────────────┐
               │ Gunicorn  │ │ React Static │
               │ (Flask)   │ │ Files        │
               │ port 5001 │ │ (build/)     │
               └─────┬─────┘ └──────────────┘
                     │
               ┌─────▼─────┐
               │  SQLite    │
               │  Database  │
               └────────────┘
```

## Directory Structure

```
ansible-playbook/
├── site.yml                          # Main playbook
├── inventory.ini                     # Target hosts
├── ansible.cfg                       # Ansible configuration
├── group_vars/
│   └── production.yml                # Production environment config
└── roles/
    ├── system-deps/                  # Python3, Node.js, Nginx, system packages
    ├── invoice-app-backend/          # Flask + Gunicorn + systemd service
    ├── database/                     # SQLite setup with safe initialization
    ├── invoice-app-frontend/         # React build + static file serving
    ├── webserver/                    # Nginx reverse proxy configuration
    └── security/                     # Firewall, SSL, CORS, secrets
```

## Prerequisites

- **Target server**: Ubuntu 20.04+ or Debian 11+
- **Ansible**: 2.12+ on the control machine
- **SSH access**: Key-based SSH access to the target server
- **Python 3**: Available on the target server

## Quick Start

### 1. Configure Inventory

Edit `inventory.ini` to add your target server:

```ini
[production]
invoice-server ansible_host=YOUR_SERVER_IP ansible_user=deploy
```

### 2. Configure Secrets

Generate secure secrets and encrypt them with Ansible Vault:

```bash
# Generate random secrets
JWT_SECRET=$(openssl rand -hex 32)
FLASK_SECRET=$(openssl rand -hex 32)

# Create an encrypted vault file
ansible-vault create group_vars/vault.yml
```

Add the following to the vault file:

```yaml
vault_jwt_secret_key: "your-generated-jwt-secret"
vault_flask_secret_key: "your-generated-flask-secret"
```

### 3. Update Domain Configuration

Edit `group_vars/production.yml` and set:

```yaml
frontend_domain: "your-actual-domain.com"
ssl_self_signed: false  # Set to false if using real certificates
ssl_certificate: "/path/to/your/certificate.crt"
ssl_certificate_key: "/path/to/your/private.key"
```

### 4. Run the Playbook

**First-time deployment** (initializes database):

```bash
ansible-playbook site.yml -e "first_time_deploy=true" --ask-vault-pass
```

**Subsequent deployments** (preserves existing database):

```bash
ansible-playbook site.yml --ask-vault-pass
```

**Deploy specific roles only**:

```bash
# Backend only
ansible-playbook site.yml --tags backend --ask-vault-pass

# Frontend only
ansible-playbook site.yml --tags frontend --ask-vault-pass

# Security updates only
ansible-playbook site.yml --tags security --ask-vault-pass
```

## Roles

### `system-deps`
Installs system packages: Python 3, pip, venv, Node.js (v18), npm, Nginx, Git, SQLite, curl, UFW, and OpenSSL. Creates the application user and base directory.

### `database`
Sets up the SQLite database with **safety guards**:
- Checks for an existing database file before initialization
- Uses a `.db_initialized` marker file to prevent accidental re-initialization
- The `first_time_deploy` flag must be explicitly set to `true` for initial setup
- Uses `db.create_all()` (safe, additive) instead of the repo's `init_db.py` which calls `db.drop_all()` (destructive)

### `invoice-app-backend`
- Clones the repository to `/opt/invoice-application`
- Creates a Python virtual environment at `src/backend/.venv`
- Installs dependencies from `requirements.txt` plus Gunicorn
- Deploys environment variables via `.env` file (mode `0600`)
- Configures Gunicorn with 3 workers
- Sets up a systemd service with security hardening (`PrivateTmp`, `ProtectSystem`, `NoNewPrivileges`)

### `invoice-app-frontend`
- Installs npm dependencies
- Builds the React app with `REACT_APP_API_URL` set to the production API URL
- Production bundle output at `src/frontend/build/`

### `webserver`
Configures Nginx to:
- Serve React static files from the build directory
- Proxy `/api/*` requests to the Gunicorn backend on port 5001
- Handle SPA routing (fallback to `index.html`)
- Enable gzip compression
- Set security headers (HSTS, X-Frame-Options, etc.)
- Redirect HTTP to HTTPS (when SSL is enabled)

### `security`
- **Firewall**: UFW configured to allow only SSH (22), HTTP (80), and HTTPS (443)
- **SSL**: Self-signed certificate generation (for testing) or bring-your-own certificates
- **CORS**: Verifies the backend is configured to restrict origins to the production domain only (no wildcard `*`)
- **Secrets**: Ensures `.env` file has restrictive permissions (`0600`)
- **SSH hardening**: Disables root login and password authentication

## Idempotency

The playbook is designed to be run multiple times safely:

- **Database**: Will NOT be re-initialized on subsequent runs (protected by marker file)
- **Services**: Handlers only restart services when configuration changes
- **Packages**: `apt` and `pip` use `state: present` (not `latest`)
- **SSL certs**: Self-signed cert uses `creates:` to skip if already present

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database URI | `sqlite:///instance/invoice_app.db` |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | Must be set via vault |
| `SECRET_KEY` | Flask session secret | Must be set via vault |
| `CORS_ORIGINS` | Allowed CORS origins | Production domain only |
| `REACT_APP_API_URL` | API URL for frontend (build-time) | `https://{domain}/api` |

## Assumptions

- Target OS is Ubuntu/Debian-based (uses `apt`)
- SSH key-based access is configured
- The deployment user has `sudo` privileges
- DNS for `frontend_domain` points to the target server
- For production, real SSL certificates are provided (Let's Encrypt, etc.)
- SQLite is acceptable for the deployment scale (single-server)

## Troubleshooting

**Backend not starting:**
```bash
sudo systemctl status invoice-backend
sudo journalctl -u invoice-backend -f
```

**Nginx errors:**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/invoice-app-error.log
```

**Database issues:**
```bash
# Check if database exists
ls -la /opt/invoice-application/src/backend/instance/

# To force re-initialization (DESTROYS ALL DATA):
# 1. Remove the marker file
sudo rm /opt/invoice-application/src/backend/instance/.db_initialized
# 2. Run with first_time_deploy flag
ansible-playbook site.yml -e "first_time_deploy=true"
```

**Health check:**
```bash
curl http://127.0.0.1:5001/api/health
```
