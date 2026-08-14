---
name: protected-dev-app-reverse-proxying
description: Safely expose a local development app to the internet behind a reverse proxy with authentication, validation, and network-boundary checks.
---

# Protected Dev App Reverse Proxying

Use this when a user wants a dev server reachable from the public internet without making the upstream app itself internet-facing.

Typical triggers:
- "Expose this local dev server publicly"
- "Put Caddy/Nginx in front of my app"
- "Password-protect the dev box"
- "Make port 9001 reachable on a hostname"

## Goal

Publish a development app through a reverse proxy with the smallest practical exposure surface:
1. proxy terminates public HTTP/TLS,
2. proxy enforces authentication,
3. upstream stays private to localhost or private networking,
4. configuration is validated before reload,
5. cloud/network rules do not bypass the proxy.

## Default workflow

1. **Inspect the current proxy config and listeners first.**
   - Find the active config file and service.
   - Verify what ports are already public.
   - Verify whether the app is already listening on `127.0.0.1` or on `0.0.0.0` / `*`.

2. **Check the upstream app’s own exposure model.**
   - Determine whether the app has real built-in auth or only route gating / development assumptions.
   - If built-in auth is incomplete, put auth at the proxy.
   - Treat route-gating flags as defense-in-depth, not as a substitute for real auth.

3. **Add a dedicated protected proxy block.**
   - Prefer a dedicated hostname.
   - Reverse proxy to the loopback upstream, e.g. `127.0.0.1:9001`.
   - Add proxy-level auth such as Caddy `basic_auth`.
   - Add a small set of safe headers if they do not conflict with the app.

4. **Validate before reload.**
   - Run config validation (`caddy validate --config ...`) before any reload.
   - Prefer formatting as part of the change (`caddy fmt --overwrite ...`) when available.
   - Do not claim success from a file edit alone.

5. **Check for proxy bypass paths.**
   - If the app listens on `*` or `0.0.0.0`, verify cloud firewall / security-group rules do **not** expose the upstream port directly.
   - Public internet should reach only 80/443 (or the explicit proxy listener), not the app port.

6. **Only reload after the config is valid and credentials are real.**
   - If the user plans to paste a real password hash later, either:
     - stop after validation with a temporary valid hash and clearly say the current password is temporary, or
     - wait to reload until the real hash is installed.

## Caddy pattern

Use `basic_auth`, not deprecated `basicauth`.

Example:

```caddy
example.com {
    encode gzip zstd

    basic_auth {
        username HASH_HERE
    }

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy no-referrer
    }

    reverse_proxy 127.0.0.1:9001
}
```

Hash generation:

```bash
caddy hash-password --algorithm argon2id
```

or

```bash
caddy hash-password --algorithm argon2id --plaintext 'REPLACE_ME'
```

Validation:

```bash
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
```

Reload only after validation succeeds:

```bash
sudo systemctl reload caddy
```

## Cloud/network checklist

For EC2-like hosts:
- DNS hostname points at the instance public IP.
- Security group allows 80/443 to the proxy.
- Security group does **not** expose the upstream app port directly if the app binds broadly.
- Host firewall rules, if present, agree with the security-group intent.

## Pitfalls

### 1. Proxy auth does not help if the upstream port is public
If the app listens on `*:9001` and the security group exposes 9001, users can bypass Caddy entirely.

### 2. Placeholder password text breaks validation
A literal placeholder in the `basic_auth` hash slot is not a valid hash and causes Caddy validation to fail. If you need a staging config before the real hash arrives, use a temporary **valid** hash and clearly tell the user it is temporary.

### 3. Deprecated Caddy syntax
`basicauth` is deprecated; use `basic_auth`.

### 4. Dev server != production app
A reverse-proxied dev server can be acceptable for private operator access, but do not describe it as production-ready if the app lacks real sessions, RBAC, CSRF protection, auditing, or route segregation.

## Verification checklist

- [ ] Active proxy config path identified.
- [ ] Upstream listener and port confirmed.
- [ ] Public hostname chosen.
- [ ] Proxy auth configured with valid hash.
- [ ] Config formatted and validated.
- [ ] Direct upstream-port exposure checked at cloud/network layer.
- [ ] Reload performed only after validation and credential readiness.
- [ ] User informed whether the result is dev-only, beta-safe, or production-safe.
