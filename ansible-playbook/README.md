# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the full-stack Invoice Application (Flask backend + React frontend) to production servers.

## Architecture

```
                    ┌──────────────┐
                    │   Internet   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Nginx (443) │
                    │  SSL + Proxy │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │ React SPA   │          │ Flask API   │
       │ (static)    │          │ (port 5001) │
       └─────────────┘          └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │   SQLite    │
                                └─────────────┘
```

## Directory Structure

```
ansible-playbook/
├── site.yml                          # Main playbook
├── inventories/
│   └── production.ini                # Production inventory
├── group_vars/
│   └── production.yml                # Production variables
└── roles/
    ├── system-deps/                  # Python3, Node.js, pip, npm, Nginx
    │   ├── tasks/main.yml
    │   └── defaults/main.yml
    ├── invoice-app-backend/          # Flask app, venv, systemd service
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   ├── templates/
    │   │   ├── backend.env.j2
    │   │   ├── gunicorn.conf.py.j2
    │   │   ├── wsgi.py.j2
    │   │   └── invoice-backend.service.j2
    │   └── defaults/main.yml
    ├── database/                     # SQLite setup with safety guards
    │   ├── tasks/main.yml
    │   ├── templates/
    │   │   └── safe_init_db.py.j2
    │   └── defaults/main.yml
    ├── invoice-app-frontend/         # React build and static serving
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   └── defaults/main.yml
    ├── webserver/                    # Nginx reverse proxy configuration
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   ├── templates/
    │   │   └── invoice-app.conf.j2
    │   └── defaults/main.yml
    └── security/                     # SSL, firewall, CORS, secrets
        ├── tasks/main.yml
        ├── handlers/main.yml
        ├── templates/
        │   └── cors_config.py.j2
        └── defaults/main.yml
```

## Prerequisites

- **Control machine**: Ansible 2.14+ installed
- **Target server**: Ubuntu 20.04+ with SSH access and sudo privileges
- **Domain name**: DNS A record pointing to the target server (for SSL)

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` and set your server IP:

```ini
[webservers]
invoice-server ansible_host=YOUR_SERVER_IP ansible_user=ubuntu
```

### 2. Set Production Secrets

Use Ansible Vault to encrypt production secrets:

```bash
# Generate secure secrets
JWT_SECRET=$(openssl rand -hex 32)
FLASK_SECRET=$(openssl rand -hex 32)

# Create encrypted variables
ansible-vault encrypt_string "$JWT_SECRET" --name 'vault_jwt_secret_key' >> group_vars/production.yml
ansible-vault encrypt_string "$FLASK_SECRET" --name 'vault_flask_secret_key' >> group_vars/production.yml
```

### 3. Update Domain Configuration

Edit `group_vars/production.yml` and set your domain:

```yaml
frontend_domain: "your-domain.com"
```

### 4. Run the Playbook

```bash
# Full deployment
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass

# Dry run (check mode)
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass --check

# Deploy specific roles only
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass --tags backend
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass --tags frontend
ansible-playbook -i inventories/production.ini site.yml --ask-vault-pass --tags security
```

## Roles

### system-deps
Installs system-level packages: Python 3, pip, Node.js 18, npm, Nginx, Certbot, and build tools.

### invoice-app-backend
- Clones the application repository
- Creates a Python virtual environment
- Installs Python dependencies from `requirements.txt`
- Installs Gunicorn as the production WSGI server
- Deploys environment configuration (`.env`)
- Sets up a systemd service for process management

### database
- Creates the SQLite database directory
- **Safely initializes the database** using `db.create_all()` instead of the repo's `init_db.py` (which calls `db.drop_all()`)
- Only initializes on first-time provisioning (checks if DB file exists)
- Creates automatic daily backups via cron
- Backs up existing database before each deployment

### invoice-app-frontend
- Installs npm dependencies
- Builds the React production bundle with `REACT_APP_API_URL` set at build time
- Serves static files via Nginx

### webserver
- Configures Nginx as a reverse proxy
- Proxies `/api/` requests to the Flask backend on port 5001
- Serves React static files with SPA routing (`try_files`)
- Caches static assets for performance
- Adds security headers

### security
- Configures UFW firewall (allows SSH, HTTP, HTTPS only)
- Manages SSL certificates via Let's Encrypt/Certbot with auto-renewal
- Restricts CORS to the production frontend domain only (replaces the `*` wildcard)
- Enforces restrictive file permissions on secrets and database
- Disables Nginx server tokens
- Applies systemd security hardening to the backend service

## Idempotency

This playbook is designed to be run multiple times safely:

- **Database**: Only initialized on first run; existing data is never dropped
- **Git clone**: Uses `force: no` to avoid overwriting local changes
- **SSL certificates**: Only obtained if not already present
- **Services**: Restarted only when configuration changes
- **Firewall**: Rules are additive and idempotent

## Key Security Considerations

1. **Secrets**: Use Ansible Vault to encrypt `vault_jwt_secret_key` and `vault_flask_secret_key`
2. **CORS**: Production restricts origins to the configured domain (no wildcard `*`)
3. **SSL**: Enforced via HTTP-to-HTTPS redirect and HSTS headers
4. **Firewall**: Only ports 22, 80, and 443 are open
5. **File permissions**: `.env` is `0600`, database is `0640`, app directory is `0750`
6. **Systemd hardening**: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`

## Deployment Assumptions

- Target OS is Ubuntu 20.04 or later (Debian-based)
- The deploying user has SSH access and sudo privileges
- A domain name is configured and DNS points to the server
- Port 80 and 443 are reachable from the internet (for Let's Encrypt)
- The application repository is publicly accessible on GitHub

## Troubleshooting

```bash
# Check backend service status
sudo systemctl status invoice-backend

# View backend logs
sudo journalctl -u invoice-backend -f
tail -f /var/log/invoice-app/gunicorn-error.log

# Check Nginx configuration
sudo nginx -t
tail -f /var/log/nginx/invoice-app-error.log

# Test backend health check directly
curl http://127.0.0.1:5001/api/health

# Check firewall status
sudo ufw status verbose

# Check SSL certificate
sudo certbot certificates
```
