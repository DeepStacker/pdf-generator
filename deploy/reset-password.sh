#!/usr/bin/env bash
#
# Recover access to the browser app when the password is lost.
#
# There is no email reset and no recovery question, on purpose: this server
# holds customers' audit workbooks and has no mail configured, so the only
# people who can reset it are the people who can already reach the host. That
# is the recovery path, and this is it in one command.
#
#   ssh <host>
#   cd ~/apps/pdf-generator/deploy && ./reset-password.sh
#
# Nothing is lost by resetting: the password protects access, not data.
set -euo pipefail

cd "$(dirname "$0")"
ENV_FILE=".env.production"
COMPOSE="podman compose -f compose.prod.yml --env-file $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
  echo "No $ENV_FILE here. Run this from the deploy directory of the checkout." >&2
  exit 1
fi

if ! podman ps --format '{{.Names}}' | grep -q '^pdfgen-app-1$'; then
  echo "pdfgen-app-1 is not running, so the hash generator is unavailable." >&2
  echo "Start the stack first:  $COMPOSE up -d" >&2
  exit 1
fi

# This rewrites the credential of the RUNNING deployment and restarts it.
# Nothing about running it from a checkout says so, and it has already been
# run by accident once -- by someone setting up a local test server who
# reached for the nearest script that makes a password hash. If you only want
# a hash, use:  podman exec -it pdfgen-app-1 python -m audit_engine_web.setpassword
if [ "${GSS_RESET_CONFIRM:-}" != "yes" ]; then
  echo
  echo "About to change the live password for $(grep -o '^TS_HOSTNAME=.*' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo 'this deployment')"
  echo "and restart the stack. Everyone signed in stays signed in; the old"
  echo "password stops working immediately."
  echo
  read -rp "Type 'change it' to continue: " CONFIRM
  [ "$CONFIRM" = "change it" ] || { echo "Cancelled."; exit 1; }
fi

echo "Setting a new password for the GSS-MIS browser app."
read -rsp "New password (at least 12 characters): " PW1; echo
read -rsp "Repeat: " PW2; echo
[ "$PW1" = "$PW2" ] || { echo "Passwords do not match." >&2; exit 1; }
[ "${#PW1}" -ge 12 ] || { echo "Use at least 12 characters: this server faces the internet." >&2; exit 1; }

# Generated inside the container so the hashing matches the running code exactly.
HASH=$(printf '%s' "$PW1" | podman exec -i pdfgen-app-1 python -c \
  'import sys; from audit_engine_web import auth; print(auth.hash_password(sys.stdin.read().strip()))')

case "$HASH" in
  pbkdf2_sha256:*) ;;
  *) echo "Unexpected hash format: $HASH" >&2; exit 1 ;;
esac

cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"

# Keep any existing GSS_SECRET_KEY: replacing it would sign out every other
# session, which is a separate decision from changing one password.
if grep -q '^GSS_AUTH_PASSWORD_HASH=' "$ENV_FILE"; then
  sed -i "s|^GSS_AUTH_PASSWORD_HASH=.*|GSS_AUTH_PASSWORD_HASH=$HASH|" "$ENV_FILE"
else
  printf '\nGSS_AUTH_PASSWORD_HASH=%s\n' "$HASH" >> "$ENV_FILE"
fi
grep -q '^GSS_SECRET_KEY=.\+' "$ENV_FILE" || \
  printf 'GSS_SECRET_KEY=%s\n' "$(podman exec pdfgen-app-1 python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Restarting the stack..."
$COMPOSE up -d >/dev/null

sleep 4
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:8080/ 2>/dev/null || echo "")
echo
echo "Done. Sign in as '${GSS_AUTH_USER:-admin}' with the new password."
echo "A backup of the previous config is alongside $ENV_FILE."
[ "$CODE" = "303" ] && echo "The gate is up (/ answered 303 to the login page)."
