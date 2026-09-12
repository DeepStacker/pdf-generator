# Runbook — GSS-MIS browser app, home server

This is the tailnet deployment. For a plain Docker host — AWS or anywhere
else, with nginx or a load balancer in front — see **[AWS.md](AWS.md)**; the
commands there are `docker`, and the stack is `compose.aws.yml`.

The stack runs under **rootless Podman** on the host, alongside unrelated
stacks. It publishes no host port: a Tailscale sidecar joins the tailnet as
its own device and proxies inward, and Funnel puts that hostname on the
public internet.

```
  internet ──▶ Tailscale Funnel ──▶ pdfgen-ts-1 ──▶ pdfgen-app-1 ──▶ /data volume
                                    (sidecar)        (Bottle, :8080)
```

| | |
|---|---|
| Host | `homeserver`, user `shivam` |
| Checkout | `~/apps/pdf-generator` |
| Compose | `deploy/compose.prod.yml`, project name `pdfgen` |
| URL | `https://pdfgengss.tailc73ec8.ts.net` |
| Data | volume `pdfgen_data` → `/data` (SQLite + logs; **no customer files**) |
| Identity | volume `pdfgen_ts_state` — the tailnet device identity. Do not delete: the node rejoins with a `-1` suffix and the URL changes. |

## First install

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
# fill in TS_AUTHKEY and the GSS_ values — see "Set or rotate the password"
```

Bring it up, then install the unit that restarts it after a reboot (rootless
Podman does not do this on its own):

```bash
cd ~/apps/pdf-generator/deploy
podman compose -f compose.prod.yml --env-file .env.production up -d --build
mkdir -p ~/.config/systemd/user
cp pdfgen.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pdfgen.service
```

## Deploy a new version

```bash
cd ~/apps/pdf-generator
git pull origin main
cd deploy
podman compose -f compose.prod.yml --env-file .env.production up -d --build
```

The image builds the browser front end from source, so there is nothing to
build or commit beforehand. Expect a couple of minutes on a cold cache.

Then check it:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://pdfgengss.tailc73ec8.ts.net/        # 303 → /login
curl -s https://pdfgengss.tailc73ec8.ts.net/api/update/check                          # version, after signing in
podman ps --filter name=pdfgen                                                        # both containers healthy
```

A `303` on `/` is correct — it means the password gate is up. A `200` with
page content means authentication is **not** enforced; stop and check
`GSS_AUTH_PASSWORD_HASH` reached the container:

```bash
podman exec pdfgen-app-1 sh -lc 'echo $GSS_AUTH_PASSWORD_HASH'
```

## Roll back

Images are tagged `latest` only, so roll back by source:

```bash
cd ~/apps/pdf-generator
git log --oneline -10
git checkout <previous-commit>
cd deploy && podman compose -f compose.prod.yml --env-file .env.production up -d --build
```

Return to the tip with `git checkout main` and rebuild. The `/data` volume is
untouched by either, so no data migration is involved.

## Locked out / forgot the password

There is no email reset and no recovery question, deliberately: this server
holds customers' audit workbooks and has no mail configured, so the only
people who can reset it are the people who can already reach the host.

```bash
ssh <host>
cd ~/apps/pdf-generator/deploy
./reset-password.sh          # asks you to type "change it" first
```

**This script changes the credential of the running deployment.** Nothing
about running it from a checkout says so, and it has already been run by
accident once. If you only want to generate a hash — to add a user, or to
set up a test instance — use this instead, which touches nothing:

```bash
podman exec -it pdfgen-app-1 python -m audit_engine_web.setpassword
```

Scripted use needs `GSS_RESET_CONFIRM=yes` to skip the prompt.

It prompts twice, writes the new hash into `.env.production` (keeping a
timestamped backup), leaves `GSS_SECRET_KEY` alone so other sessions are not
disturbed, restarts the stack and checks the gate came back up.

Nothing is lost by resetting — the password protects access, not data. The
volume, the history and the configuration are untouched.

If the host itself is unreachable, there is no other way in, and that is the
intended property: possession of the server is the credential of last resort.

## Set or rotate the password

```bash
podman exec -it pdfgen-app-1 python -m audit_engine_web.setpassword
```

It prints a `GSS_AUTH_PASSWORD_HASH` and a `GSS_SECRET_KEY`. Put them in
`deploy/.env.production` and restart:

```bash
podman compose -f compose.prod.yml --env-file .env.production up -d
```

Notes:

- The password is never stored — only a PBKDF2-SHA256 hash of it.
- The hash deliberately contains no `$`. Compose interpolates `$NAME` inside
  env file values, and the conventional `$`-separated PBKDF2 format was
  silently mangled on the way into the container, which rejected every
  password including the right one. Keep any replacement free of `$`.
- Changing `GSS_SECRET_KEY` signs everyone out. Leaving it unset signs
  everyone out on every restart.

## Logs

```bash
podman logs -f pdfgen-app-1           # application
podman logs -f pdfgen-ts-1            # tailnet / funnel
podman exec pdfgen-app-1 tail -f /data/audit_engine.log
```

Failed logins are logged with the client address.

## Take it off the public internet

Set `AllowFunnel` to `false` in `deploy/ts-serve.json`, then:

```bash
podman compose -f compose.prod.yml --env-file .env.production restart ts
podman exec pdfgen-ts-1 tailscale serve status     # should no longer say "Funnel on"
```

It stays reachable from the tailnet.

## What is on disk

`/data` holds the SQLite database, the job tracker and the log. It holds **no
customer files**: uploads are deleted when their job ends, generated reports
seconds after they are served, and an idle sweeper clears anything abandoned.
To confirm at any time:

```bash
podman exec pdfgen-app-1 sh -lc 'find /tmp/audit_engine_* -type f; find /data -type f'
```

Between runs the first command should print nothing.
