#!/usr/bin/env bash
# First-run setup for a plain Docker host. Clone, run this, answer one
# question, and the stack is up.
#
#   ./deploy/bootstrap.sh
#
# It creates deploy/.env.production from the template, generates the password
# hash and the cookie signing key, and starts the stack. Run it again later
# and it leaves an existing password alone -- use ./deploy/reset-password.sh
# to change one.
#
# It never writes the password anywhere. What lands in the env file is a
# PBKDF2 hash, which cannot be turned back into the password.
set -euo pipefail

cd "$(dirname "$0")"
COMPOSE_FILE="compose.aws.yml"
ENV_FILE=".env.production"

die() { printf '\n%s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "Docker is not installed. See deploy/AWS.md."
docker compose version >/dev/null 2>&1 || die "This Docker has no 'compose' subcommand. Install Docker Compose v2."
docker info >/dev/null 2>&1 || die "Cannot talk to the Docker daemon. Is it running, and is this user in the docker group?"

compose() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

if [ ! -f "$ENV_FILE" ]; then
    cp .env.production.example "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "Created deploy/$ENV_FILE from the template."
fi

current_hash=$(grep -E '^GSS_AUTH_PASSWORD_HASH=' "$ENV_FILE" | cut -d= -f2- || true)

if [ -n "$current_hash" ]; then
    echo "A password is already configured. Leaving it alone."
else
    echo "The server refuses every request until a password is set."
    if [ -t 0 ]; then
        # Read twice, never echo, never let it reach the command line.
        read -r -s -p "New password (at least 12 characters): " password; echo
        read -r -s -p "Repeat: " repeat; echo
        [ "$password" = "$repeat" ] || die "Those do not match. Nothing was changed."
    else
        read -r password
    fi
    [ -n "$password" ] || die "No password given. Nothing was changed."

    echo "Building the image (a few minutes the first time)..."
    # --no-deps so this does not start the rest of the stack just to hash a
    # string, and -T so the piped password is read from stdin.
    generated=$(printf '%s\n' "$password" | compose run --rm --no-deps -T app python -m audit_engine_web.setpassword) \
        || die "Could not generate the hash. The output above says why."
    unset password repeat

    hash_line=$(printf '%s\n' "$generated" | grep -E '^GSS_AUTH_PASSWORD_HASH=' || true)
    key_line=$(printf '%s\n' "$generated" | grep -E '^GSS_SECRET_KEY=' || true)
    [ -n "$hash_line" ] && [ -n "$key_line" ] || die "The generator printed no hash. Nothing was changed."

    # Replace both lines in place, whatever they currently hold.
    tmp=$(mktemp)
    trap 'rm -f "$tmp"' EXIT
    awk -v h="$hash_line" -v k="$key_line" '
        /^GSS_AUTH_PASSWORD_HASH=/ { print h; next }
        /^GSS_SECRET_KEY=/         { print k; next }
        { print }
    ' "$ENV_FILE" > "$tmp"
    cat "$tmp" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "Password set. The hash is in deploy/$ENV_FILE; the password itself is stored nowhere."
fi

echo "Starting the stack..."
compose up -d --build

port=$(grep -E '^HOST_PORT=' "$ENV_FILE" | cut -d= -f2- || true)
port=${port:-8080}

echo
echo "Waiting for it to come up..."
for _ in $(seq 1 60); do
    state=$(docker inspect --format '{{.State.Health.Status}}' pdfgen-app-1 2>/dev/null || echo starting)
    [ "$state" = "healthy" ] && break
    sleep 2
done

if [ "${state:-}" = "healthy" ]; then
    echo "Up. It answers on port $port, and every page needs the password."
    echo "Check it with:  curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:$port/     # 303 is correct"
else
    echo "It did not become healthy. What it says:" >&2
    docker logs --tail 30 pdfgen-app-1 >&2 || true
    exit 1
fi
