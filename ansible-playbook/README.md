# Invoice Application - Ansible Deployment Playbook

Automated deployment playbook for the full-stack Invoice Application (Flask + React + Nginx).

## Architecture

```
Client Browser
    │
    ▼
┌─────────┐      ┌──────────────────┐      ┌────────────┐
│  Nginx   │─────▶│  Flask/Gunicorn  │─────▶│   SQLite   │
│ (HTTPS)  │ API  │   (port 5001)    │      │  Database   │
│          │proxy │                  │      └────────────┘
│  Static  │      └──────────────────┘
│  Files   │
│ (React)  │
└─────────┘
```

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ (or Debian-based)
- SSH access to the target server with sudo privileges

### Install Ansible (on your control machine)

```bash
pip install ansible
```

## Quick Start

### 1. Configure Inventory

Edit `inventory.ini` with your target server details:

```ini
[production]
invoice-server ansible_host=YOUR_SERVER_IP ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2. Set Production Secrets

**Option A: Using ansible-vault (recommended)**

```bash
# Create an encrypted vault file
ansible-vault create group_vars/vault.yml
```

Add the following to the vault file:

```yaml
vault_jwt_secret_key: "your-secure-random-string"
vault_flask_secret_key: "another-secure-random-string"
```

Then update `group_vars/production.yml` to reference vault variables:

```yaml
jwt_secret_key: "{{ vault_jwt_secret_key }}"
flask_secret_key: "{{ vault_flask_secret_key }}"
```

**Option B: Using `--extra-vars` at runtime**

```bash
ansible-playbook -i inventory.ini site.yml \
  --extra-vars "jwt_secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  --extra-vars "flask_secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

### 3. Run the Playbook

```bash
# Full deployment
ansible-playbook -i inventory.ini site.yml

# With vault password
ansible-playbook -i inventory.ini site.yml --ask-vault-pass

# Dry run (check mode)
ansible-playbook -i inventory.ini site.yml --check

# Deploy specific roles using tags
ansible-playbook -i inventory.ini site.yml --tags "backend"
ansible-playbook -i inventory.ini site.yml --tags "frontend"
ansible-playbook -i inventory.ini site.yml --tags "webserver"
```

## Role Descriptions

| Role | Tag | Description |
|------|-----|-------------|
| `system-deps` | `system` | Installs Python3, Node.js 18, npm, Nginx, SQLite, and build tools |
| `security` | `security` | Configures UFW firewall, SSL certificates, CORS restrictions, and application user |
| `database` | `database` | Sets up SQLite with **safe initialization** (no `drop_all()`) and automated backups |
| `invoice-app-backend` | `backend` | Deploys Flask app with virtualenv, Gunicorn, and systemd service |
| `invoice-app-frontend` | `frontend` | Builds React app with production API URL and serves static files |
| `webserver` | `webserver` | Configures Nginx as reverse proxy with HTTPS, SPA routing, and static caching |

## Key Design Decisions

### Database Safety

The original `init_db.py` calls `db.drop_all()` which would destroy all data on every run. This playbook uses a **safe initialization script** that:
- Only runs `db.create_all()` (creates tables without dropping existing ones)
- Only executes on first-time provisioning (when the database file doesn't exist)
- Creates automatic backups before each deployment

### CORS Hardening

The application's default CORS configuration allows all origins (`*`). This playbook restricts CORS to the production frontend domain only via a production config override.

### Service Management

The Flask development server (`app.run(debug=True)`) is replaced with **Gunicorn** (3 workers) managed by **systemd**, with:
- Automatic restart on failure
- Security hardening (PrivateTmp, NoNewPrivileges, ProtectSystem)
- Structured logging to `/var/log/invoice-app/`

### SSL/TLS

- Generates a self-signed certificate on first deployment
- Configured for easy upgrade to Let's Encrypt via `certbot`
- HTTP automatically redirects to HTTPS

## Directory Layout on Target Server

```
/opt/invoice-application/          # Application root
├── src/backend/                   # Flask backend
│   ├── instance/invoice_app.db    # SQLite database
│   └── production_config.py       # Production CORS config
├── src/frontend/build/            # React production build
├── .venv/                         # Python virtual environment
└── backups/                       # Database backups

/etc/invoice-app/env               # Environment secrets
/etc/systemd/system/invoice-backend.service
/etc/nginx/sites-available/invoice-app.conf
/var/log/invoice-app/              # Application logs
```

## Idempotency

This playbook is designed to be run multiple times safely:
- Database initialization only runs if the DB file doesn't exist
- `db.create_all()` only creates missing tables
- npm and pip installs are incremental
- Systemd services are restarted only when configuration changes
- Database is backed up before each redeployment

## SSL Certificate Upgrade (Let's Encrypt)

After initial deployment with the self-signed certificate:

```bash
# On the target server
sudo certbot --nginx -d your-domain.com

# Then update group_vars/production.yml with the certbot paths:
# nginx_ssl_cert_path: /etc/letsencrypt/live/your-domain.com/fullchain.pem
# nginx_ssl_key_path: /etc/letsencrypt/live/your-domain.com/privkey.pem
```

## Troubleshooting

```bash
# Check backend service status
sudo systemctl status invoice-backend

# View backend logs
sudo journalctl -u invoice-backend -f

# Check Nginx status
sudo systemctl status nginx
sudo nginx -t

# View application logs
tail -f /var/log/invoice-app/error.log

# Test backend health endpoint
curl http://localhost:5001/api/health

# Manually reinitialize database (CAUTION: only if needed)
sudo -u invoice-app /opt/invoice-application/.venv/bin/python \
  /opt/invoice-application/src/backend/safe_init_db.py
```
