# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the full-stack Invoice Application (Flask backend + React frontend) to production servers.

## Architecture

```
Client  -->  Nginx (port 80/443)
               |
               ├── /api/*  -->  Gunicorn/Flask (port 5001)  -->  SQLite DB
               └── /*      -->  React static files (build/)
```

## Directory Structure

```
ansible-playbook/
├── site.yml                          # Main playbook entry point
├── inventory.ini                     # Target host inventory
├── group_vars/
│   └── production.yml                # Production environment variables
└── roles/
    ├── system-deps/                  # Python3, Node.js, Nginx, system packages
    │   └── tasks/main.yml
    ├── invoice-app-backend/          # Flask app, virtualenv, gunicorn, systemd
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   └── templates/
    │       ├── backend.env.j2
    │       ├── gunicorn.conf.py.j2
    │       └── invoice-backend.service.j2
    ├── invoice-app-frontend/         # React build and static file setup
    │   ├── tasks/main.yml
    │   └── handlers/main.yml
    ├── database/                     # SQLite setup with init safety guards
    │   └── tasks/main.yml
    ├── webserver/                    # Nginx reverse proxy + static serving
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   └── templates/
    │       └── invoice-app.nginx.conf.j2
    └── security/                     # UFW firewall, SSL, CORS, hardening
        ├── tasks/main.yml
        ├── handlers/main.yml
        └── templates/
            └── config_production.py.j2
```

## Prerequisites

- **Control machine**: Ansible 2.12+ with Python 3
- **Target server**: Ubuntu 20.04+ or Debian 11+
- **Network**: SSH access with sudo privileges to the target server

## Quick Start

### 1. Configure Inventory

Edit `inventory.ini` with your server details:

```ini
[production]
invoice-prod ansible_host=YOUR_SERVER_IP ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2. Set Production Secrets

**Option A** - Use Ansible Vault (recommended):

```bash
# Create an encrypted vault file
ansible-vault create group_vars/vault.yml
```

Add these variables to the vault:

```yaml
jwt_secret_key: "<generated-64-char-hex-string>"
flask_secret_key: "<generated-64-char-hex-string>"
```

Generate secure keys with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Option B** - Use `--extra-vars` at runtime:

```bash
ansible-playbook -i inventory.ini site.yml \
  --extra-vars "jwt_secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
  --extra-vars "flask_secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

### 3. Update Domain Configuration

Edit `group_vars/production.yml` and set your actual domain:

```yaml
frontend_domain: "invoice.yourdomain.com"
```

### 4. Run the Playbook

```bash
# Full deployment
ansible-playbook -i inventory.ini site.yml

# With vault password
ansible-playbook -i inventory.ini site.yml --ask-vault-pass

# Deploy specific roles only
ansible-playbook -i inventory.ini site.yml --tags backend
ansible-playbook -i inventory.ini site.yml --tags frontend
ansible-playbook -i inventory.ini site.yml --tags security
```

## Roles Overview

| Role | Purpose |
|------|---------|
| `system-deps` | Installs Python 3, Node.js, npm, Nginx, and creates the application user |
| `database` | Sets up SQLite with **safety guards** to prevent `init_db.py` from destroying data on redeploys |
| `invoice-app-backend` | Clones repo, creates virtualenv, installs deps, configures gunicorn + systemd |
| `invoice-app-frontend` | Runs `npm ci` and `npm run build` with the production API URL baked in |
| `webserver` | Configures Nginx as reverse proxy for API + static file server for React SPA |
| `security` | UFW firewall, Let's Encrypt SSL, CORS lockdown, SSH hardening |

## Key Design Decisions

### Database Safety

The application's `init_db.py` calls `db.drop_all()` which would destroy all data. The `database` role:
1. Checks for an existing SQLite database file
2. Checks for a `.db_initialized` marker file
3. Only initializes the schema on first-time provisioning
4. Uses `create_app()` (which calls `db.create_all()`) instead of `init_db.py` to avoid the destructive `drop_all()` call

### Production WSGI Server

The playbook uses **Gunicorn** instead of Flask's built-in debug server. The systemd service ensures the backend:
- Starts on boot
- Restarts on failure
- Runs with restricted file system access (systemd hardening)

### CORS Restriction

The development configuration allows all origins (`*`). The security role deploys a production CORS config that restricts origins to only the configured `frontend_domain`.

### SSL / TLS

By default, SSL is enabled and uses Let's Encrypt (certbot) to obtain certificates. Set `ssl_enabled: false` in `group_vars/production.yml` for environments without a public domain.

## Idempotency

The playbook is designed to be run multiple times safely:
- Database initialization only happens once (marker file guard)
- `npm ci` and `npm run build` are re-run but are non-destructive
- Systemd services are restarted only when configuration changes
- Nginx configuration is validated before reload

## Troubleshooting

```bash
# Check backend service status
sudo systemctl status invoice-backend
sudo journalctl -u invoice-backend -f

# Check Nginx status
sudo systemctl status nginx
sudo nginx -t

# Check application logs
tail -f /var/log/invoice-app/error.log
tail -f /var/log/invoice-app/access.log

# Test backend health endpoint directly
curl http://127.0.0.1:5001/api/health
```
