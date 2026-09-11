"""Generate the values the browser server's password gate expects.

    python -m audit_engine_web.setpassword

Prints the two environment lines to paste into .env.production. The password
itself is only ever typed here; what gets stored is a PBKDF2 hash, so the
config file cannot give the password back to anyone who reads it.
"""

import getpass
import secrets
import sys

from audit_engine_web import auth


def main() -> int:
    if sys.stdin.isatty():
        password = getpass.getpass("New password: ")
        if not password:
            print("No password entered.", file=sys.stderr)
            return 1
        if password != getpass.getpass("Repeat: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    else:
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            print("No password on stdin.", file=sys.stderr)
            return 1

    if len(password) < 12:
        print("Use at least 12 characters: this server faces the internet.", file=sys.stderr)
        return 1

    print()
    print("Add these to deploy/.env.production, then restart the stack:")
    print()
    print(f"{auth.PASSWORD_ENV}={auth.hash_password(password)}")
    print(f"{auth.SECRET_ENV}={secrets.token_urlsafe(32)}")
    print()
    print("GSS_SECRET_KEY signs session cookies. Keep it stable, or everyone")
    print("is signed out on every restart. Changing it signs everyone out on purpose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
