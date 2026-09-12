# Deploying on AWS

One EC2 instance running Docker. The app publishes a port, nginx sits in
front of it, and TLS is terminated either by nginx or by a load balancer.

```
  clients ──▶ [ ALB, or nginx :443 ] ──▶ app :8080 ──▶ /data volume
                                                        (SQLite + logs)
```

For the home-server stack on the tailnet, see [RUNBOOK.md](RUNBOOK.md)
instead. Everything below is the plain-Docker path.

## Before you start

| | |
|---|---|
| Instance | 2 vCPU / 4 GB is comfortable. Merging holds a whole branch in memory. |
| Disk | 20 GB. The image is about 1.2 GB; customer files are never kept. |
| Ports in | 443 (and 80, only if nginx is getting its own certificate). Never expose 8080 to the internet. |
| Ports out | 443, to pull images. The app itself needs no outbound access. |
| Software | Docker Engine with the `compose` plugin. |

Install Docker:

```bash
# Amazon Linux 2023
sudo dnf install -y docker docker-compose-plugin git
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # log out and back in

# Ubuntu 24.04
curl -fsSL https://get.docker.com | sudo sh
sudo apt-get install -y git
sudo usermod -aG docker "$USER"   # log out and back in
```

## Deploy

```bash
git clone https://github.com/DeepStacker/pdf-generator.git
cd pdf-generator
./deploy/bootstrap.sh
```

It asks for one thing, a password, and does the rest: writes
`deploy/.env.production`, turns the password into a hash, generates the cookie
signing key, builds the image and starts the stack. The first build takes a
few minutes because it compiles nothing but downloads pandas and builds the
browser front end.

Check it:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/   # 303 → /login is correct
docker compose -f deploy/compose.aws.yml ps                       # app healthy
```

A `303` means the password gate is up. A `200` with page content would mean it
is not; stop and check that `GSS_AUTH_PASSWORD_HASH` reached the container:

```bash
docker exec pdfgen-app-1 printenv GSS_AUTH_PASSWORD_HASH
```

## Put TLS in front of it

The session cookie is `Secure`, so a browser will not keep it over plain
HTTP. **Signing in only works over HTTPS.** Two ways to get there.

### With an AWS load balancer

The balancer terminates TLS and forwards to the instance. Point its target
group at port 8080, or at port 80 with the nginx profile running:

```bash
docker compose -f deploy/compose.aws.yml --env-file deploy/.env.production --profile proxy up -d
```

Set `BIND_ADDRESS=127.0.0.1` in `deploy/.env.production` when nginx is in
front, so the app's own port is not reachable from outside the host at all.
Health check path `/`, expect 200 or 303.

### With nginx holding the certificate

Get a certificate however you normally do. With certbot on the host:

```bash
sudo dnf install -y certbot            # or: sudo apt-get install -y certbot
sudo certbot certonly --standalone -d audit.example.com
```

Copy the two files where the container can read them, and tell nginx to use
the TLS config:

```bash
sudo cp /etc/letsencrypt/live/audit.example.com/{fullchain,privkey}.pem deploy/certs/
sudo chown "$USER" deploy/certs/*.pem
sed -i 's/^NGINX_CONF=.*/NGINX_CONF=app-tls.conf/' deploy/.env.production
docker compose -f deploy/compose.aws.yml --env-file deploy/.env.production --profile proxy up -d
```

Certbot's own files are symlinks into `../../archive`, which do not survive
being mounted, hence the copy. Renew with a hook that re-copies and reloads:

```bash
sudo certbot renew --deploy-hook '
  cp /etc/letsencrypt/live/audit.example.com/{fullchain,privkey}.pem /home/ec2-user/pdf-generator/deploy/certs/
  docker exec pdfgen-nginx-1 nginx -s reload'
```

## Day to day

```bash
# Update to the latest code
git pull origin main
docker compose -f deploy/compose.aws.yml --env-file deploy/.env.production up -d --build

# Logs
docker logs -f pdfgen-app-1
docker exec pdfgen-app-1 tail -f /data/audit_engine.log

# Add or remove users: the Users screen in the app, signed in as the admin.

# Change the password
docker compose -f deploy/compose.aws.yml run --rm --no-deps app python -m audit_engine_web.setpassword
# then paste both lines into deploy/.env.production and `up -d` again.

# Back up (accounts and settings; no customer files are kept)
docker run --rm -v pdfgen_pdfgen_data:/data -v "$PWD":/backup alpine \
    tar czf /backup/pdfgen-data-$(date +%F).tar.gz -C /data .
```

`deploy/reset-password.sh` exists for the home server and drives `podman`. On
Docker use the `setpassword` command above instead.

## Things worth knowing before you scale it

- **One instance.** Accounts, settings and the job tracker live in SQLite on
  this host's volume. Two instances behind a balancer would not share users,
  and a session issued by one would confuse the other. Scale up, not out.
- **One request at a time.** The app runs Bottle's reference server, which is
  single-threaded. nginx in front absorbs slow uploads, but a long merge does
  hold the server. That is fine for a team; it is not a public API.
- **Nothing customer-owned is stored.** Uploads are deleted when their job
  ends, generated files seconds after they are served, and a sweeper clears
  anything abandoned. The volume holds the database and the log only.
- **The image contains the whole repo**, including the desktop app and tests.
  That is deliberate: the server reads templates, fonts and settings from the
  source tree at runtime.

## When it will not start

| What you see | What it is |
|---|---|
| `container pdfgen-app-1 is unhealthy` and the log says `NOT CONFIGURED` | No password hash. Run `./deploy/bootstrap.sh`, or generate one with `setpassword`. |
| Every page returns 503 | Same thing: `GSS_AUTH_PASSWORD_HASH` is empty in the environment the container actually got. |
| The login form takes the right password and returns to the login page | You are on plain HTTP, so the browser is dropping the `Secure` cookie. Put TLS in front. For a throwaway test only, set `GSS_COOKIE_SECURE=false`. |
| `413 Request Entity Too Large` | Something in front of nginx has its own body limit. The ALB has none; a proxy you added might. |
| Upload dies at exactly 60 seconds | A proxy timeout, not the app. `deploy/nginx/app.conf` already allows 900s. |
| `permission denied` on `/data` | The container runs as uid 10001. Use the named volume rather than a bind mount, or `chown -R 10001:10001` the directory you bind. |
