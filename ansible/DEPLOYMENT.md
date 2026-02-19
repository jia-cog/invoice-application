# Invoice Application - Ansible Deployment Guide

## Overview

This Ansible playbook automates the complete deployment of the Invoice Application, a Flask/React web application for invoice management. It handles system setup, database configuration, backend deployment, frontend builds, and security hardening.

## Architecture

```
[Client Browser] --> [Nginx :80/:443]
                        |
                        |--> /api/* --> [Gunicorn :5001] --> [PostgreSQL :5432]
                        |
                        |--> /* --> [React Static Build]
```

## Design Decisions

### Production Database: PostgreSQL
- ACID-compliant with full transaction support
- Handles concurrent connections required for multi-user invoice management
- Native JSON support for the Report model's data field
- Industry standard for production Flask applications
- Robust backup and replication capabilities

### Web Server: Nginx
- Lightweight with low memory footprint
- Excellent reverse proxy performance for API routing
- Built-in static file serving with caching headers
- Native SSL termination support
- Battle-tested in production environments

### SSL Strategy: Let's Encrypt via Certbot
- Free, automated certificate issuance and renewal
- Certbot integrates directly with Nginx
- Automated renewal via cron job
- Widely trusted certificate authority

### Secrets Management: Ansible Vault
- Encrypted at rest with AES-256
- Integrated into Ansible workflow
- Secrets validated at deploy time (non-default, minimum length)
- Environment-specific vault files per deployment tier

### Target Infrastructure: Ubuntu/Debian VM
- Most common target for Ansible automation
- Minimum recommended specs:
  - **Development**: 1 vCPU, 1GB RAM, 10GB disk
  - **Staging**: 2 vCPU, 2GB RAM, 20GB disk
  - **Production**: 4 vCPU, 4GB RAM, 50GB disk

### Deployment Strategy: Sequential with Health Checks
- Acceptable brief downtime during deployment
- Health check verification after each service starts
- Rollback possible via git branch revert and re-deploy

## Directory Structure

```
ansible/
├── site.yml                          # Main playbook
├── ansible.cfg                       # Ansible configuration
├── DEPLOYMENT.md                     # This file
├── inventories/
│   ├── development/hosts.yml         # Dev inventory
│   ├── staging/hosts.yml             # Staging inventory
│   └── production/hosts.yml          # Production inventory
├── group_vars/
│   ├── all/
│   │   ├── main.yml                  # Shared variables
│   │   └── vault.yml.example         # Vault template
│   ├── development/main.yml          # Dev overrides
│   ├── staging/main.yml              # Staging overrides
│   └── production/main.yml           # Production overrides
└── roles/
    ├── system_setup/                 # Python, Node.js, system deps
    ├── database_config/              # PostgreSQL setup
    ├── backend_deploy/               # Flask + Gunicorn + systemd
    ├── frontend_build/               # React build + Nginx config
    └── security_hardening/           # SSL, firewall, secrets
```

## Prerequisites

1. **Control machine**: Ansible 2.15+ installed
2. **Target server**: Ubuntu 22.04+ with SSH access and sudo privileges
3. **Network**: Ports 22, 80, 443 accessible

Install required Ansible collections:

```bash
ansible-galaxy collection install community.postgresql community.general ansible.posix
```

## Quick Start

### 1. Set Up Secrets

```bash
cd ansible/

# Create vault file from template
cp group_vars/all/vault.yml.example group_vars/all/vault.yml

# Edit with your secrets
cat > group_vars/all/vault.yml << EOF
vault_db_password: "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
vault_jwt_secret_key: "$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
vault_flask_secret_key: "$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
EOF

# Encrypt the vault file
ansible-vault encrypt group_vars/all/vault.yml
```

### 2. Configure Inventory

Edit the appropriate inventory file for your environment:

```bash
# For staging
vim inventories/staging/hosts.yml
```

Update `ansible_host`, `ansible_user`, and `ansible_ssh_private_key_file`.

### 3. Deploy

```bash
# Development (local)
ansible-playbook site.yml -i inventories/development/hosts.yml

# Staging
ansible-playbook site.yml -i inventories/staging/hosts.yml --ask-vault-pass

# Production
ansible-playbook site.yml -i inventories/production/hosts.yml --ask-vault-pass
```

## Role Details

### system_setup
- Updates apt cache and installs system dependencies
- Installs Python 3, pip, and venv tools
- Adds NodeSource repository and installs Node.js 20
- Creates dedicated `invoice` user and group
- Sets up application directory structure at `/opt/invoice-application`

### database_config
- Installs and configures PostgreSQL 16
- Creates database user and database with proper privileges
- Configures `pg_hba.conf` for application access
- Sets up automated daily backups with retention policy (30 days)
- Verifies database connectivity

### backend_deploy
- Clones the application repository
- Creates Python virtual environment and installs dependencies
- Installs Gunicorn and psycopg2 for production serving
- Deploys environment file with production secrets (DATABASE_URL, JWT_SECRET_KEY, etc.)
- Creates Gunicorn config with configurable workers, timeouts, and logging
- Deploys systemd service unit for process management
- Runs `init_db.py` to initialize database tables (users, invoices, invoice_items, reports)
- Verifies backend health via `/api/health` endpoint

### frontend_build
- Installs npm dependencies from `package.json`
- Builds React app with `REACT_APP_API_URL` pointed to production domain
- Installs and configures Nginx as reverse proxy
- Routes `/api/*` requests to Gunicorn backend on port 5001
- Serves React static build for all other routes with SPA fallback
- Adds security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Configures static asset caching (1 year expiry)
- Supports SSL termination when enabled

### security_hardening
- Validates production secrets are non-default and >= 32 characters
- Restricts file permissions on `.env` and config files (0600)
- Installs and configures UFW firewall (ports 22, 80, 443)
- Obtains Let's Encrypt SSL certificate via Certbot
- Sets up automated certificate renewal cron job
- Applies kernel sysctl hardening (production only)
- Disables unnecessary services
- Configures CORS for production domains

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `app_domain` | *required* | Domain name for the application |
| `app_env` | `development` | Environment (development/staging/production) |
| `db_password` | *required* | PostgreSQL database password |
| `jwt_secret_key` | *required* | JWT authentication secret |
| `flask_secret_key` | *required* | Flask session secret |
| `backend_port` | `5001` | Gunicorn listen port |
| `gunicorn_workers` | `3` | Number of Gunicorn worker processes |
| `enable_ssl` | `false` | Enable Let's Encrypt SSL |
| `enable_firewall` | `true` | Enable UFW firewall |
| `cors_origins` | `https://{domain}` | Allowed CORS origins |
| `nodejs_version` | `20` | Node.js major version |

## Troubleshooting

### Check service status
```bash
systemctl status invoice-backend
systemctl status nginx
systemctl status postgresql
```

### View logs
```bash
journalctl -u invoice-backend -f
tail -f /opt/invoice-application/logs/gunicorn-access.log
tail -f /var/log/nginx/invoice-app-error.log
```

### Health check
```bash
curl http://localhost:5001/api/health
```

### Database connection
```bash
sudo -u postgres psql -d invoice_app -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
```
