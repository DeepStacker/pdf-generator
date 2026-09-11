# GSS-MIS

Bank audit report generation. One Python backend, two front ends:

| | How it runs | Who uses it |
|---|---|---|
| **Desktop** | A native window (pywebview). No HTTP server, no network. | Auditors, on their own machines |
| **Browser** | A Bottle server in a container | Same work, from a phone or any browser |

Both drive the same handlers and the same report generators, so a fix to a
bank's output lands in both at once.

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

deploy/                    Compose stack, systemd unit, env template
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

## Deployment

See **[deploy/RUNBOOK.md](deploy/RUNBOOK.md)**.

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
