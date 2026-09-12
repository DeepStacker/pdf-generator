# GSS-MIS

Bank audit report generation. One Python backend, two front ends:

| | How it runs | Who uses it |
|---|---|---|
| **Desktop** | A native window (pywebview). No HTTP server, no network. | Auditors, on their own machines |
| **Browser** | A Bottle server in a container | Same work, from a phone or any browser |

Both drive the same handlers and the same report generators, so a fix to a
bank's output lands in both at once.

## Deploy it on a server

Any Linux host with Docker on it — an EC2 instance, or anything else.

**Before you start:** 2 CPUs, 4 GB of memory and 20 GB of disk; ports 443 (and
80, only if this server will fetch its own certificate) open to your users;
port 8080 open to nobody.

**1. Install Docker**, then log out and back in so the group change takes
effect.

```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker "$USER"
```

That script covers Ubuntu and Debian. On Amazon Linux 2023, install the
packages instead — the exact commands are in [deploy/AWS.md](deploy/AWS.md).

**2. Get the code.**

```bash
git clone https://github.com/DeepStacker/pdf-generator.git
```

**3. Run the setup script.** It asks for a password once — twelve characters
or more — and then builds the image and starts everything. The first run takes
a few minutes. Nothing else is needed: no config file to edit, no secret to be
sent to you.

```bash
cd pdf-generator && ./deploy/bootstrap.sh
```

**4. Check it came up.** `303` is the right answer. It means the login page is
in front of everything.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
```

**5. Put HTTPS in front of it.** Either an AWS load balancer that terminates
TLS, or the nginx that ships with this stack holding your certificate. Both
are written out step by step in **[deploy/AWS.md](deploy/AWS.md)**.

> **Signing in only works over HTTPS.** The session cookie is marked `Secure`,
> so on a plain `http://` address the browser throws it away and the login
> page comes back as though the password were wrong. It is not; there is no
> TLS yet. This is the one thing that surprises people.

**6. Sign in** at your domain as `admin`, with the password from step 3, and
add everyone else from the Users screen.

If it will not start, the end of [deploy/AWS.md](deploy/AWS.md) lists what
each failure means — and the application says why in its own log:

```bash
docker logs pdfgen-app-1
```

### Updating it later

```bash
git pull origin main && docker compose -f deploy/compose.aws.yml --env-file deploy/.env.production up -d --build
```

### The home server

The machine on the tailnet runs a different stack: Podman, and a Tailscale
sidecar instead of a published port. That one is
**[deploy/RUNBOOK.md](deploy/RUNBOOK.md)**.

## Layout

```
src/audit_engine/          Shared backend — all business logic
├── services/              Per-bank report generation (IDFC, Equitas, Arvog),
│                          the report validator, the PDF flattener,
│                          the branch-folder PDF merger
├── consolidator/          Multi-workbook consolidation
├── tasks/workers.py       The job workers all three banks run through
├── web/                   The /api/* handlers, shared by both front ends
├── __main__.py            Desktop entry point
└── ui/static/             Desktop front end
    ├── index.html, app.js
    ├── tokens.css         ← the palette, read by BOTH front ends
    └── web.css            ← the components, read by BOTH front ends

web/                       Browser front end (React 19, Vite, Tailwind 4)
└── src/index.css          imports the two stylesheets above

audit_engine_web/          Browser server (Bottle)
├── __main__.py            routes, the password gate, zero-retention handling
├── auth.py                password hashing and sessions
├── patches.py             disables desktop-only handlers in web mode
└── static/                BUILD OUTPUT — generated, not in git

deploy/                    bootstrap.sh, the two compose stacks, nginx, env template
```

The desktop has no HTTP server: `ui/__init__.py` inlines `tokens.css`,
`web.css` and `app.js` into a single HTML file, writes it to a temp path and
opens it over `file://`. That is why the two front ends share stylesheets but
not a bundle.

## Development

```bash
pip install -e ".[dev]"          # Python
cd web && npm ci                 # browser front end
```

| Task | Command |
|---|---|
| Run the desktop app | `python -m audit_engine` |
| Run the browser app | `cd web && npm run build` then `python -m audit_engine_web` |
| Front end, live reload | `cd web && npm run dev` (proxies `/api` to port 8080) |
| Tests | `python -m pytest tests/ -q` |
| Lint | `python -m ruff check src/ tests/` |
| Typecheck the front end | `cd web && npm run lint` |

CI runs exactly `ruff check src/ tests/`, `pytest tests/`, and a
build + typecheck of `web/`. Run those three before pushing.

**The browser bundle is not committed.** It is built from `web/` — by the
Dockerfile for deployment, and by CI on every push. Editing `web/src` and
deploying is enough; there is nothing to rebuild by hand.

## Security posture

Read this before exposing the browser app anywhere new.

- **Forgotten password?** `deploy/reset-password.sh` on the host. There is no
  email reset by design; whoever can reach the server can reset it, and
  nothing is lost by doing so. See the runbook.
- **It requires a password.** Every route except the login page and the icons
  needs a session. With `GSS_AUTH_PASSWORD_HASH` unset the server refuses
  every request rather than serving openly, so a deploy that forgets it fails
  loudly instead of publishing customer data.
- **It is on the public internet** via Tailscale Funnel
  (`deploy/ts-serve.json`). Set `AllowFunnel` to `false` to make it
  tailnet-only again.
- **It keeps no customer files.** An uploaded workbook is deleted when its job
  ends, a generated report seconds after it is served, and an idle sweeper
  clears anything abandoned. Nothing customer-owned is written to the
  persistent volume.
- **It records no customer filenames.** The run history is disabled in web
  mode: on a shared server it listed one visitor's workbook names to the next.
  The desktop keeps its history, where the data never leaves the machine.
- **The service worker never caches `/api/`**, so no report can end up stored
  in a browser after the server has deleted it.

The desktop app is unaffected by all of the above. It opens no socket.

## Known issues

- Podman builds OCI images and ignores the Dockerfile `HEALTHCHECK`. The
  compose stack defines its own, so the deployed stack is still health-checked.
