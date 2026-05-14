## Note on Mobile Access and Gateways

The private HTTP API/tunnel remains the correct mobile access surface for Context Vault Engine. MCP stdio remains local-only and must not be exposed over the network. The planned OpenAI-compatible context gateway (see ROADMAP.md, Phase 46) will be an optional, disabled-by-default adapter for OpenAI-compatible clients. It will not replace the HTTP API or change the core deployment model.
# Context Vault Engine - Private Cloud Mode Deployment Guide

> **Security warning:** Never expose an unauthenticated Context Vault Engine API to the public internet. Always use one of the access models described below when running on a remote server.

## Overview

Context Vault Engine supports an optional **Private Cloud Mode** that allows you to run the engine on a personal VPS or private server and access it from trusted clients without exposing unauthenticated write-capable APIs.

Private Cloud Mode is:

- **Opt-in** - disabled by default; local behaviour is unchanged.
- **Read-only by default** - mutating routes are blocked unless explicitly enabled.
- **Token-authenticated** - API requests require a bearer token you configure.
- **Self-hosted** - no cloud accounts, no SaaS, no databases, no multi-tenancy.

The MCP stdio server (`python run.py mcp`) remains a local stdin/stdout process and is not affected by private cloud mode.

---

## Security Model

| Concern | Approach |
|---------|----------|
| API authentication | Bearer token from environment variable |
| Token storage | Environment only - never committed, never logged |
| Secret exposure | Token value never appears in responses or status output |
| Mutating access | Blocked by default in remote mode (`CVE_REMOTE_READ_ONLY=true`) |
| TLS/HTTPS | Handled by reverse proxy or tunnel - **not** by FastAPI directly |
| Public exposure | Must be behind one of the access models below |
| Path traversal | Existing server-side protection unchanged |
| Rate limiting | Existing 50 req/s global limiter unchanged |

---

## Recommended Access Models

Do not expose the API port directly on a public IP. Use one of:


### 1. Tailscale (recommended for personal use)

Install [Tailscale](https://tailscale.com/) on both server and client. The server is only reachable via your private Tailscale network.

> **Caution:** Tailscale only provides the private network path. It does **not** control or enable Private Cloud Mode. Private Cloud Mode is controlled by Context Vault Engine environment/configuration. For tunnel/API testing, always launch from a terminal/session with deliberate Private Cloud configuration. Do not assume Tailscale alone will protect unauthenticated APIs.

```bash
# On the VPS
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Context Vault Engine listens on localhost only
# Your Tailscale IP (e.g. 100.x.x.x) reaches it via Tailscale
```
---

> **Note:** Tailscale status does not affect Private Cloud Mode. Always verify the Context Vault Engine runtime mode using `/private/status` or by inspecting environment variables. Tunnel/API testing should use explicit Private Cloud configuration.

### 2. WireGuard

Set up a WireGuard VPN between your server and trusted clients. Bind the server to the WireGuard interface address.

### 3. Cloudflare Tunnel with Cloudflare Access

Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), create a tunnel, and use Cloudflare Access to restrict who can reach the tunnel endpoint.

```bash
cloudflared tunnel create context-vault
cloudflared tunnel route dns context-vault vault.example.com
```

Add a Cloudflare Access policy requiring your email or mTLS certificate before traffic even reaches the server.

### 4. Nginx Reverse Proxy with HTTPS

Use a public-CA certificate (e.g. Let's Encrypt via Certbot) and require HTTPS at the Nginx layer.

```nginx
server {
    listen 443 ssl;
    server_name vault.example.com;

    ssl_certificate     /etc/letsencrypt/live/vault.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vault.example.com/privkey.pem;

    # Do not expose the API port directly; proxy to localhost only
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name vault.example.com;
    return 301 https://$host$request_uri;
}
```

### 5. Caddy Reverse Proxy with Automatic HTTPS

[Caddy](https://caddyserver.com/) handles TLS automatically via Let's Encrypt.

```caddy
vault.example.com {
    reverse_proxy localhost:8000
}
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CVE_PRIVATE_CLOUD_ENABLED` | Enable private cloud mode | `false` |
| `CVE_AUTH_TOKEN` | Secret bearer token for API authentication | _(empty - auth disabled)_ |
| `CVE_REQUIRE_AUTH` | Require auth for all non-health API routes | `false` in local mode; `true` when private cloud enabled |
| `CVE_REMOTE_READ_ONLY` | Block all mutating HTTP routes | `true` when private cloud enabled |
| `CVE_PUBLIC_BASE_URL` | Public base URL (for status display only) | _(empty)_ |
| `CVE_DEPLOYMENT_MODE` | Deployment mode tag: `local`, `vps`, or `tunnel` | `local` |

### Token generation

Generate a strong random token:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# or
openssl rand -hex 32
```

**Never commit the token to version control.** Store it only in:
- A `.env` file excluded by `.gitignore`
- A systemd `EnvironmentFile`
- Your secret manager

---

## Local Private-Mode Example

Test private cloud mode locally before deploying to a VPS:

```bash
# Generate a token
TOKEN=$(python -c "import secrets; print(secrets.token_hex(32))")

# Start the server with private cloud mode enabled
CVE_PRIVATE_CLOUD_ENABLED=true \
CVE_AUTH_TOKEN="$TOKEN" \
CVE_REMOTE_READ_ONLY=true \
CVE_DEPLOYMENT_MODE=local \
python run.py app

# Verify status (no auth required for /private/status)
curl http://localhost:8000/private/status

# Authenticated read request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/vaults

# Alternative token header
curl -H "X-CVE-Token: $TOKEN" http://localhost:8000/vaults

# Unauthenticated request - returns 401
curl http://localhost:8000/vaults

# Write request in read-only mode - returns 403
curl -X PUT -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}' \
     http://localhost:8000/note
```

---

## VPS systemd Service Example

Create `/etc/systemd/system/context-vault.service`:

```ini
[Unit]
Description=Context Vault Engine
After=network.target

[Service]
Type=simple
User=vault
WorkingDirectory=/opt/context-vault-engine
EnvironmentFile=/opt/context-vault-engine/.env.private
ExecStart=/opt/context-vault-engine/.venv/bin/python run.py app
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/context-vault-engine

[Install]
WantedBy=multi-user.target
```

Create `/opt/context-vault-engine/.env.private` (mode 600, owned by the service user):

```bash
CVE_PRIVATE_CLOUD_ENABLED=true
CVE_AUTH_TOKEN=<your-generated-token>
CVE_REQUIRE_AUTH=true
CVE_REMOTE_READ_ONLY=true
CVE_DEPLOYMENT_MODE=vps
CVE_PUBLIC_BASE_URL=https://vault.example.com
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable context-vault
sudo systemctl start context-vault
sudo systemctl status context-vault
```

---

## Firewall Guidance

Block port 8000 from public access; only allow it from localhost so the reverse proxy can reach it:

```bash
# Allow only local access to the API port
sudo ufw deny 8000
sudo ufw allow 443
sudo ufw allow 80
sudo ufw enable
```

If using Tailscale, ensure the firewall allows the Tailscale interface:

```bash
sudo ufw allow in on tailscale0
```

---

## Backup Guidance

Phase 38 ships a first-class local backup and restore surface. The built-in
backup is local-only, preview-first, and stdlib-only:

- `py run.py backup --preview` prints a JSON plan (no files written).
- `py run.py backup --write` writes a zip to
  `dist/backups/cve-backup-<utc>-<id>.zip` with `backup-manifest.json` at
  the root and SHA-256 per file. Generated artefacts (`dist/`,
  `node_modules/`, caches, `.git/`, vault reports) are excluded.
- `py run.py backup --list` lists existing local backups.
- `py run.py restore --backup <id> --preview` shows every target with
  `target_exists` / `would_overwrite` and any blocking errors or
  migration warnings.
- `py run.py restore --backup <id> --write --overwrite --confirm "RESTORE <id>"`
  applies the restore. Existing files are never replaced without
  `--overwrite` and a matching `--confirm` phrase. `config/config.yaml`
  is only restored when `--restore-config` is also passed. Files are
  hash-validated in a temporary directory before live targets are
  replaced.

The built-in backup never uploads anywhere. Treat
`dist/backups/cve-backup-*.zip` as private artefacts and copy them
off-host using your normal backup tooling if you need offsite copies.

The persistent state that must be backed up:

| Path | Contents |
|------|---------|
| `<repo>/config/config.yaml` | Vault registry and server settings |
| `<repo>/demo-vault/` | Demo vault notes and feedback |
| `<repo>/<vault-name>/` | Your custom vault notes, feedback, and schema |
| `.env.private` | Environment variables (store separately, encrypted) |

Example backup script (run as a cron job):

```bash
#!/bin/bash
BACKUP_DIR=/var/backups/context-vault
REPO=/opt/context-vault-engine
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/vault-$DATE.tar.gz" \
    "$REPO/config/" \
    "$REPO/demo-vault/" \
    "$REPO"/*-vault/ \
    --exclude="$REPO"/*/.git \
    2>/dev/null

# Keep 14 days of backups
find "$BACKUP_DIR" -name "vault-*.tar.gz" -mtime +14 -delete
```

---

## Update Procedure

```bash
# Stop the service
sudo systemctl stop context-vault

# Pull updates
cd /opt/context-vault-engine
git pull

# Update Python dependencies
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r mcp/requirements.txt

# Rebuild the UI if changed
cd ui
npm install
npm run build
cd ..

# Run verification
python run.py validate
python run.py security

# Restart the service
sudo systemctl start context-vault
```

---

## Verifying Your Deployment

### 1. Health check (no auth required)

```bash
curl https://vault.example.com/health
```

Expected: `{"status": "ok", "data": {...}}`

### 2. Private cloud status (no auth required)

```bash
curl https://vault.example.com/private/status
```

Expected response when correctly configured:

```json
{
  "status": "ok",
  "data": {
    "enabled": true,
    "deployment_mode": "vps",
    "require_auth": true,
    "token_configured": true,
    "remote_read_only": true,
    "public_base_url": "https://vault.example.com",
    "warnings": [],
    "protected_methods": ["PUT", "POST", "DELETE"]
  }
}
```

### 3. Authenticated read request

```bash
curl -H "Authorization: Bearer $TOKEN" \
     https://vault.example.com/vaults
```

Expected: `{"status": "ok", "data": {"vaults": ["demo-vault"]}}`

### 4. Unauthenticated request - must return 401

```bash
curl https://vault.example.com/vaults
```

Expected:

```json
{
  "status": "error",
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "Authentication required. ..."
  }
}
```

### 5. Write attempt in read-only mode - must return 403

```bash
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"vault":"demo-vault","path":"test","source":"human","signal":"unclear","severity":"low","comment":"test"}' \
     https://vault.example.com/feedback
```

Expected:

```json
{
  "status": "error",
  "error": {
    "code": "REMOTE_READ_ONLY",
    "message": "Remote read-only mode blocks this operation."
  }
}
```

---

## MCP Client Note

The HTTP API described in this guide is private-cloud capable and can be used by trusted remote clients via HTTPS and bearer token authentication.

The MCP stdio server (`python run.py mcp`) uses JSON-RPC 2.0 over stdin/stdout. It is designed for local use only and is not affected by private cloud mode settings. Do not attempt to expose the stdio server over a network socket - it has no authentication.

---

## Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All requests return 401 | `CVE_AUTH_TOKEN` not set or empty | Generate and set a token |
| `/private/status` shows `token_configured: false` | Token env var not exported to the process | Check `EnvironmentFile` or shell export |
| Write requests return 403 even with auth | `CVE_REMOTE_READ_ONLY=true` (default) | Set `CVE_REMOTE_READ_ONLY=false` only if you need writes remotely |
| `warnings` contains deployment_mode=local warning | `CVE_DEPLOYMENT_MODE` not set | Set `CVE_DEPLOYMENT_MODE=vps` or `tunnel` |
| HTTPS not working | TLS is handled by the proxy, not FastAPI | Verify Nginx/Caddy/Cloudflare config |
