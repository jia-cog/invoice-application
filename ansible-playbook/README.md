# Invoice Application - Ansible Deployment Playbook

This Ansible playbook automates the deployment of the full-stack Invoice Application, consisting of a Flask (Python) backend and a React.js frontend, onto a production server.

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ (Debian-based)
- SSH access to the target server with sudo privileges
- Python 3.8+ on the target server

## Directory Structure

```
ansible-playbook/
├── site.yml                           # Main playbook
├── README.md                          # This file
├── inventories/
│   └── production.ini                 # Production inventory
├── group_vars/
│   └── production.yml                 # Production environment config
└── roles/
    ├── system-deps/                   # Python3, Node.js, pip, npm, Nginx
    ├── security/                      # SSL, firewall (UFW), fail2ban, secrets
    ├── database/                      # SQLite setup with safe initialization
    ├── invoice-app-backend/           # Flask app, venv, Gunicorn, systemd
    ├── invoice-app-frontend/          # React build, static file serving
    └── webserver/                     # Nginx reverse proxy configuration
```

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` and replace `YOUR_SERVER_IP` with your target server's IP address:

```ini
[invoice_servers]
invoice-prod-01 ansible_host=192.168.1.100 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2. Configure Secrets with Ansible Vault

Create an encrypted vault file for production secrets:

```bash
ansible-vault create group_vars/vault.yml
```

Add the following variables:

```yaml
vault_jwt_secret_key: "your-secure-jwt-secret-here"
vault_flask_secret_key: "your-secure-flask-secret-here"
```

Generate secure secrets with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Update Production Configuration

Edit `group_vars/production.yml` to set your production domain and any other environment-specific values:

```yaml
server_domain: "invoices.yourdomain.com"
```

### 4. Run the Playbook

```bash
# Full deployment
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass

# Deploy specific roles using tags
ansible-playbook -i inventories/production.ini site.yml --tags backend --ask-vault-pass
ansible-playbook -i inventories/production.ini site.yml --tags frontend --ask-vault-pass

# Dry run (check mode)
ansible-playbook -i inventories/production.ini site.yml --check --ask-vault-pass
```

## Available Tags

| Tag        | Description                          |
|------------|--------------------------------------|
| `system`   | System dependencies only             |
| `security` | SSL, firewall, secrets               |
| `database` | Database setup and initialization    |
| `backend`  | Flask backend deployment             |
| `frontend` | React frontend build and deployment  |
| `webserver`| Nginx configuration                  |

## Roles Overview

### system-deps
Installs system-level packages: Python 3, pip, venv, Node.js (v18), npm, Nginx, SQLite, and build tools.

### security
- Configures UFW firewall (allows SSH, HTTP, HTTPS only)
- Generates self-signed SSL certificate (for initial setup; replace with Let's Encrypt for production)
- Deploys environment file with secrets (read from Ansible Vault)
- Configures fail2ban for Nginx protection
- Restricts CORS to the production frontend domain only (fixes the wildcard `*` origin issue)

### database
- Creates the SQLite database directory with correct ownership
- **Safe initialization**: Checks if the database already exists and has tables before initializing. Uses `db.create_all()` (non-destructive) instead of `init_db.py` which calls `db.drop_all()` (destructive)
- Sets up automated daily backups with 30-day retention
- Configures a cron job for backup scheduling

### invoice-app-backend
- Clones/updates the application repository
- Creates a Python virtual environment at `.venv`
- Installs dependencies from `requirements.txt` plus Gunicorn
- Deploys Gunicorn configuration for production WSGI serving
- Creates a systemd service (`invoice-backend`) with security hardening (no new privileges, private tmp, read-only filesystem)
- Manages service lifecycle (start, restart on config changes)

### invoice-app-frontend
- Installs npm dependencies via `npm ci`
- Sets `REACT_APP_API_URL` environment variable at **build time** to the production API URL
- Runs `npm run build` to create the production bundle
- Verifies the build directory was created successfully

### webserver
- Removes the default Nginx site
- Deploys a production Nginx configuration that:
  - Redirects HTTP to HTTPS
  - Serves React static files from the build directory
  - Proxies `/api/*` requests to the Flask backend on port 5001
  - Handles SPA routing with `try_files $uri $uri/ /index.html`
  - Applies aggressive caching for static assets (1 year)
  - Disables caching for `index.html` (so new deployments are picked up)
  - Sets security headers (HSTS, X-Frame-Options, X-Content-Type-Options, etc.)
  - Enables gzip compression

## Idempotency

This playbook is designed to be run multiple times safely:

- **Database**: The initialization guard checks for existing tables and only creates the schema on first run. It never calls `db.drop_all()`.
- **Backend**: The systemd service is only restarted when configuration changes are detected.
- **Frontend**: The build runs on each deployment to ensure the latest code is served.
- **Nginx**: Configuration is validated before reload.

## SSL Certificates

The playbook generates a self-signed certificate for initial setup. For production use with a real domain:

1. Ensure your domain DNS points to the server
2. Run: `sudo certbot --nginx -d yourdomain.com`
3. Certbot will automatically configure Nginx with a valid Let's Encrypt certificate

## Assumptions

- Target server is Ubuntu/Debian-based with `apt` package manager
- The application repository is publicly accessible (or SSH keys are configured for private access)
- SQLite is used as the database (suitable for low-to-medium traffic; consider PostgreSQL for high traffic)
- The server has at least 1GB RAM and 10GB disk space
- Port 22 (SSH), 80 (HTTP), and 443 (HTTPS) are accessible

## Troubleshooting

### Check backend service status
```bash
sudo systemctl status invoice-backend
sudo journalctl -u invoice-backend -f
```

### Check Nginx status
```bash
sudo systemctl status nginx
sudo nginx -t
sudo tail -f /var/log/nginx/invoice-app-error.log
```

### Check application logs
```bash
sudo tail -f /var/log/invoice-app/gunicorn-access.log
sudo tail -f /var/log/invoice-app/gunicorn-error.log
```

### Verify health check
```bash
curl http://127.0.0.1:5001/api/health
```
