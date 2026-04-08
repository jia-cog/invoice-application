# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the full-stack Invoice Application to production servers.

## Architecture

| Component | Technology | Details |
|-----------|-----------|---------|
| Backend | Flask + Gunicorn | Python API on port 5001 (behind Nginx) |
| Frontend | React.js | Static build served by Nginx |
| Database | SQLite | File-based, located in `instance/` |
| Web Server | Nginx | Reverse proxy + static file server |
| Process Manager | systemd | Manages the Gunicorn backend service |
| Auth | JWT | 24-hour token expiration |

## Directory Structure

```
ansible-playbook/
├── site.yml                              # Main playbook
├── README.md                             # This file
├── inventories/
│   └── production.ini                    # Inventory of target servers
├── group_vars/
│   └── production.yml                    # Production environment config
└── roles/
    ├── system-deps/                      # Python3, Node.js, Nginx, system packages
    ├── invoice-app-backend/              # Flask app, venv, Gunicorn, systemd service
    ├── invoice-app-frontend/             # React build with production API URL
    ├── database/                         # SQLite setup with safe initialization
    ├── webserver/                        # Nginx reverse proxy + static serving
    └── security/                         # UFW firewall, SSL, CORS, fail2ban
```

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ (Debian-based)
- **SSH access**: Key-based authentication to target servers
- **DNS**: Domain pointing to the target server (for SSL)

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` to add your server(s):

```ini
[invoice_servers]
invoice-prod ansible_host=YOUR_SERVER_IP ansible_user=ubuntu
```

### 2. Configure Production Variables

Edit `group_vars/production.yml` and **update at minimum**:

```yaml
# REQUIRED: Generate secure secrets before deploying
jwt_secret_key: "<generate with: python3 -c 'import secrets; print(secrets.token_urlsafe(64))'>"
flask_secret_key: "<generate with: python3 -c 'import secrets; print(secrets.token_urlsafe(64))'>"

# REQUIRED: Set your production domain
frontend_domain: "your-domain.com"
```

### 3. First-Time Deployment

For initial deployment, enable database schema creation:

```bash
ansible-playbook -i inventories/production.ini site.yml \
  -e "db_initialize_schema=true"
```

### 4. Subsequent Deployments

For redeployments (code updates, config changes):

```bash
ansible-playbook -i inventories/production.ini site.yml
```

The database will **not** be re-initialized on subsequent runs.

## Role Details

### system-deps
Installs Python3, pip, Node.js (v18), npm, Nginx, SQLite, Certbot, UFW, and creates the application user/group.

### invoice-app-backend
- Clones the repository to `/opt/invoice-application`
- Creates a Python virtual environment at `src/backend/.venv`
- Installs dependencies from `requirements.txt` plus Gunicorn
- Deploys environment variables via `.env` file (mode 0600)
- Configures a systemd service (`invoice-backend`) running Gunicorn
- Gunicorn binds to `127.0.0.1:5001` (not exposed directly)

### invoice-app-frontend
- Installs npm dependencies from `src/frontend/package.json`
- Sets `REACT_APP_API_URL` at build time to the production backend URL
- Runs `npm run build` to create the production bundle
- Static files are served from `src/frontend/build/`

### database
- Creates the SQLite database directory with proper permissions
- **Safety guard**: Schema initialization only runs when:
  1. `db_initialize_schema` is explicitly set to `true`, AND
  2. The database file does not already exist
- Uses `db.create_all()` directly (avoids the destructive `db.drop_all()` in `init_db.py`)
- Warns if re-initialization is requested on an existing database

### webserver
- Removes the default Nginx site
- Deploys a production Nginx configuration:
  - Serves React static files with SPA routing (`try_files`)
  - Proxies `/api/` requests to the Flask backend
  - Caches static assets (JS, CSS, images) for 30 days
  - HTTP to HTTPS redirect (when SSL is enabled)
- Includes security headers (X-Frame-Options, X-Content-Type-Options, etc.)

### security
- **Firewall (UFW)**: Allows only SSH (22), HTTP (80), and HTTPS (443)
- **SSL**: Obtains Let's Encrypt certificates via Certbot with auto-renewal
- **CORS**: Deploys a production CORS config restricting origins to the frontend domain only (replaces the default wildcard `*`)
- **Secrets**: Ensures `.env` and database files have restrictive permissions
- **Fail2ban**: Installed and enabled for SSH brute-force protection

## Tags

Run specific parts of the playbook using tags:

```bash
# Only update backend
ansible-playbook -i inventories/production.ini site.yml --tags backend

# Only update frontend
ansible-playbook -i inventories/production.ini site.yml --tags frontend

# Only update security
ansible-playbook -i inventories/production.ini site.yml --tags security
```

Available tags: `system`, `database`, `backend`, `frontend`, `webserver`, `security`

## Idempotency

This playbook is designed to be run multiple times safely:
- Package installations use `state: present` (not `latest`)
- Database initialization is guarded by file existence checks
- Systemd services are only restarted when configuration changes
- SSL certificates are only obtained if they don't already exist
- Firewall rules are applied idempotently by UFW

## Security Considerations

1. **Secrets**: Always generate unique `jwt_secret_key` and `flask_secret_key` values for production. Never use the defaults.
2. **SSL**: The playbook configures Let's Encrypt with auto-renewal. Ensure port 80 is accessible for ACME challenges.
3. **CORS**: Production configuration restricts origins to the frontend domain only.
4. **Database**: SQLite database file permissions are set to `0640` (owner read/write, group read).
5. **Firewall**: Only SSH, HTTP, and HTTPS are allowed by default.

## Assumptions

- Target servers run Ubuntu/Debian with `apt` package manager
- SSH key-based authentication is configured
- The deployment user has `sudo` privileges
- DNS is configured to point the frontend domain to the server
- Port 80 is accessible for Let's Encrypt certificate issuance
