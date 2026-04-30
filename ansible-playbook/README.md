# Invoice Application - Ansible Deployment Playbook

Ansible playbook for deploying the Invoice Application (Flask + React) to a production server.

## Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │
                    │  (SSL/TLS)  │
                    └──┬──────┬───┘
                       │      │
              ┌────────▼┐  ┌──▼────────┐
              │  React  │  │  /api/*   │
              │ Static  │  │  Proxy    │
              │ Files   │  └──┬────────┘
              └─────────┘     │
                       ┌──────▼──────┐
                       │  Gunicorn   │
                       │  (Flask)    │
                       └──────┬──────┘
                              │
                       ┌──────▼──────┐
                       │   SQLite    │
                       └─────────────┘
```

## Directory Structure

```
ansible-playbook/
├── ansible.cfg                       # Ansible configuration
├── site.yml                          # Main playbook
├── inventories/
│   └── production.ini                # Target host inventory
├── group_vars/
│   └── production.yml                # Production variables
└── roles/
    ├── system-deps/                  # Python3, Node.js, Nginx, system packages
    ├── security/                     # Firewall, SSL, secrets management, CORS
    ├── database/                     # SQLite setup with safe initialization
    ├── invoice-app-backend/          # Flask app, venv, Gunicorn, systemd
    ├── invoice-app-frontend/         # React build with production API URL
    └── webserver/                    # Nginx reverse proxy + static file serving
```

## Prerequisites

- **Control machine**: Ansible 2.12+ installed
- **Target server**: Ubuntu 20.04+ with SSH access and sudo privileges
- A registered domain name pointing to the target server's IP address

Install required Ansible collections:

```bash
ansible-galaxy collection install community.general
```

## Quick Start

### 1. Configure Inventory

Edit `inventories/production.ini` with your server details:

```ini
[production]
invoice-server ansible_host=YOUR_SERVER_IP ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2. Set Production Secrets

Create an Ansible Vault file for secrets:

```bash
ansible-vault create group_vars/vault.yml
```

Add the following variables:

```yaml
jwt_secret_key: "your-secure-random-jwt-secret-here"
flask_secret_key: "your-secure-random-flask-secret-here"
```

Generate secure random secrets:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Update Production Variables

Edit `group_vars/production.yml` and update:

- `server_domain` - your production domain
- `letsencrypt_email` - email for SSL certificate notifications
- `app_repo_branch` - the branch to deploy (defaults to `main`)

### 4. Run the Playbook

Full deployment:

```bash
cd ansible-playbook
ansible-playbook site.yml --ask-vault-pass
```

Deploy specific roles using tags:

```bash
# Only backend
ansible-playbook site.yml --tags backend --ask-vault-pass

# Only frontend
ansible-playbook site.yml --tags frontend --ask-vault-pass

# Only webserver (Nginx)
ansible-playbook site.yml --tags webserver --ask-vault-pass
```

### 5. Verify Deployment

The playbook automatically verifies the backend health endpoint. You can also check manually:

```bash
curl https://your-domain.com/api/health
```

## Role Details

### system-deps
Installs Python 3, pip, Node.js (v18), npm, Nginx, UFW, certbot, SQLite, and creates the application user/group.

### security
- Configures UFW firewall (allows SSH, HTTP, HTTPS; denies direct backend access)
- Obtains and auto-renews Let's Encrypt SSL certificates
- Manages application secrets via a protected environment file
- Restricts CORS to the production frontend domain only

### database
- Creates the SQLite database directory with correct permissions
- **Safety guard**: Only initializes the schema on first-time provisioning (skips `init_db.py` which calls `db.drop_all()`)
- Uses `db.create_all()` directly to safely create tables without dropping existing data
- Sets up daily database backups with 30-day retention
- Creates a pre-deployment backup on every redeploy

### invoice-app-backend
- Clones/updates the application repository
- Creates a Python virtual environment and installs dependencies
- Installs Gunicorn for production WSGI serving (replaces Flask debug server)
- Deploys a systemd service for process management and auto-restart

### invoice-app-frontend
- Installs npm dependencies from `src/frontend/package.json`
- Sets `REACT_APP_API_URL` at build time to the production API URL
- Runs `npm run build` to create the production bundle

### webserver
- Configures Nginx as a reverse proxy
- Serves React static files from the build directory
- Proxies `/api/*` requests to the Gunicorn backend
- Handles SPA routing (serves `index.html` for all non-file routes)
- Adds gzip compression and security headers
- Supports SSL with HTTP-to-HTTPS redirect

## Idempotency

This playbook is designed to be run multiple times safely:

- **Database**: Only initialized on first run; existing data is preserved on redeploys
- **Backups**: A pre-deployment backup is created before every redeploy
- **Services**: Handlers only restart services when configuration actually changes
- **SSL**: Certificates are only obtained if they don't already exist
- **Firewall**: Rules are idempotent and won't duplicate

## Assumptions

- Target server runs Ubuntu 20.04 or later
- The server has outbound internet access (for apt, npm, pip, and Let's Encrypt)
- SSH key-based authentication is configured for the deploy user
- The deploy user has passwordless sudo access
- DNS is configured to point `server_domain` to the target server's IP
- SQLite is sufficient for the deployment scale (for high-traffic scenarios, consider migrating to PostgreSQL)

## Troubleshooting

Check service status:

```bash
sudo systemctl status invoice-backend
sudo systemctl status nginx
```

View application logs:

```bash
sudo journalctl -u invoice-backend -f
tail -f /var/log/invoice-app/access.log
tail -f /var/log/nginx/invoice-app-error.log
```

Test Nginx configuration:

```bash
sudo nginx -t
```

Manually verify the database:

```bash
sqlite3 /opt/invoice-application/src/backend/instance/invoice_app.db ".tables"
```
