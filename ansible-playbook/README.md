# Invoice Application - Ansible Deployment Playbook

This Ansible playbook automates the deployment of the Invoice Application, a full-stack invoicing system with a Flask backend, React frontend, and SQLite database.

## Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │
                    │  (SSL/TLS) │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐     ┌─────────▼─────────┐
     │  React Static   │     │  Flask API (/api)  │
     │  Files (/)      │     │  via Gunicorn      │
     └─────────────────┘     │  port 5001         │
                             └─────────┬──────────┘
                                       │
                             ┌─────────▼──────────┐
                             │  SQLite Database    │
                             └────────────────────┘
```

## Directory Structure

```
ansible-playbook/
├── site.yml                          # Main playbook
├── README.md                         # This file
├── inventories/
│   └── production.ini                # Production inventory
├── group_vars/
│   └── production.yml                # Production variables
└── roles/
    ├── system-deps/                  # Python3, Node.js, pip, npm, Nginx
    ├── security/                     # SSL, firewall, secrets, CORS
    ├── database/                     # SQLite setup with safety guards
    ├── invoice-app-backend/          # Flask app, venv, Gunicorn, systemd
    ├── invoice-app-frontend/         # React build, static file setup
    └── webserver/                    # Nginx reverse proxy configuration
```

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ (Debian-based)
- **Network**: SSH access to target server
- **Permissions**: Sudo/root access on target server

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` and add your server:

```ini
[invoice_servers]
invoice-prod-01 ansible_host=YOUR_SERVER_IP ansible_user=ubuntu
```

### 2. Configure Variables

Edit `group_vars/production.yml` to set your production values:

```yaml
# REQUIRED: Update these for your environment
frontend_domain: "invoice.yourdomain.com"
jwt_secret_key: "your-secure-random-secret"
flask_secret_key: "your-secure-random-secret"
```

**Important**: For production deployments, use Ansible Vault to encrypt secrets:

```bash
# Create an encrypted vault file for secrets
ansible-vault create group_vars/vault.yml

# Add your secrets:
# jwt_secret_key: "your-very-long-random-secret-key"
# flask_secret_key: "another-very-long-random-secret-key"
```

### 3. First-Time Deployment

For the initial deployment, set `first_time_provision=true` to initialize the database:

```bash
ansible-playbook -i inventories/production.ini site.yml \
  -e "first_time_provision=true" \
  --ask-become-pass
```

### 4. Subsequent Deployments

For redeployments (code updates, config changes), run without the provision flag:

```bash
ansible-playbook -i inventories/production.ini site.yml --ask-become-pass
```

This safely updates the application without touching the database.

## Role Details

### system-deps
Installs system packages: Python3, pip, Node.js (v18), npm, Nginx, UFW, and build tools.

### security
- Configures UFW firewall (allows SSH, HTTP, HTTPS only)
- Generates self-signed SSL certificate (replace with Let's Encrypt for production)
- Creates a dedicated `invoice` service account
- Deploys environment files with restricted permissions (0600)
- Restricts CORS to production frontend domain only (replaces the default `*` wildcard)

### database
- Creates the SQLite database directory with proper ownership
- **Safety guard**: Only runs `init_db.py` when BOTH conditions are met:
  1. `first_time_provision=true` is explicitly passed
  2. The database file does not already exist
- Sets up daily backups with 7-day retention via cron
- This prevents the destructive `db.drop_all()` call from wiping data on redeployments

### invoice-app-backend
- Clones/updates the application repository
- Creates Python virtual environment at `.venv`
- Installs dependencies from `requirements.txt` (falls back to explicit package list)
- Deploys Gunicorn WSGI configuration (replaces Flask debug server)
- Sets up systemd service with security hardening (PrivateTmp, NoNewPrivileges, etc.)

### invoice-app-frontend
- Installs npm dependencies
- Builds React production bundle with `REACT_APP_API_URL` set to production backend URL
- Sets proper file permissions for Nginx to serve static files

### webserver
- Configures Nginx as reverse proxy
- Serves React static files from the build directory
- Proxies `/api/*` requests to the Flask/Gunicorn backend on port 5001
- Handles SPA routing (serves `index.html` for all non-API, non-static routes)
- HTTP-to-HTTPS redirect
- Security headers (HSTS, X-Frame-Options, etc.)
- Gzip compression

## Tags

Run specific parts of the playbook using tags:

```bash
# Only update backend
ansible-playbook -i inventories/production.ini site.yml --tags backend

# Only update frontend
ansible-playbook -i inventories/production.ini site.yml --tags frontend

# Only update Nginx config
ansible-playbook -i inventories/production.ini site.yml --tags webserver

# Only update security settings
ansible-playbook -i inventories/production.ini site.yml --tags security
```

## Idempotency

This playbook is designed to be run multiple times safely:

- **Database**: Protected by dual safety guards (flag + file existence check)
- **Services**: Only restarted when configuration actually changes (via handlers)
- **Packages**: Only installed/upgraded when needed (state: present)
- **SSL certificates**: Only generated if they don't already exist

## SSL Certificates

The playbook generates a self-signed SSL certificate by default. For production:

1. **Let's Encrypt**: Replace the self-signed cert with a proper certificate:
   ```bash
   ansible-playbook -i inventories/production.ini site.yml \
     -e "nginx_ssl_cert=/etc/letsencrypt/live/yourdomain/fullchain.pem" \
     -e "nginx_ssl_key=/etc/letsencrypt/live/yourdomain/privkey.pem"
   ```

2. **Disable SSL** (not recommended): Set `nginx_enable_ssl: false` in `group_vars/production.yml`

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
```

### Check application logs
```bash
tail -f /var/log/invoice-app/gunicorn-access.log
tail -f /var/log/invoice-app/gunicorn-error.log
tail -f /var/log/invoice-app/nginx-access.log
tail -f /var/log/invoice-app/nginx-error.log
```

### Health check
```bash
curl http://127.0.0.1:5001/api/health
```

## Assumptions

- Target server runs Ubuntu 20.04+ (Debian-based)
- SSH access with sudo privileges is available
- The server has internet access to clone the repository and install packages
- DNS for `frontend_domain` is configured to point to the server
- SQLite is acceptable for the deployment scale (for high traffic, consider PostgreSQL)
