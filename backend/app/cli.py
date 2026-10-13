"""Management commands.

python -m app.cli seed-demo [--password PW]     demo companies, vacancies and accounts (development)
python -m app.cli create-admin EMAIL NAME       creates an administrator; asks for the password
"""

import argparse
import getpass
import os
import sys

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.services.auth_service import create_user


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-demo", help="Insert demo data (never in production)")
    seed.add_argument("--password", help="Password for the demo accounts (default: SEED_DEMO_PASSWORD or a generated one)")
    admin = sub.add_parser("create-admin", help="Create an administrator account")
    admin.add_argument("email")
    admin.add_argument("name")
    args = parser.parse_args()

    if args.command == "seed-demo":
        if get_settings().is_production:
            sys.exit("Refusing to seed demo data in production.")
        from app.seed.seed import run

        with SessionLocal() as db:
            result = run(db, args.password or os.environ.get("SEED_DEMO_PASSWORD"))
        print(f"Demo vacancies created: {result['jobs_created']}")
        for email in result["accounts_created"]:
            print(f"Demo account: {email}")
        if result["accounts_created"] and result["password_generated"]:
            print(f"Generated password for the demo accounts (shown once): {result['password']}")
    elif args.command == "create-admin":
        password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password (min. 10 characters): ")
        if len(password) < 10:
            sys.exit("Password must be at least 10 characters.")
        with SessionLocal() as db:
            user = create_user(db, email=args.email, password=password, full_name=args.name, role=UserRole.ADMIN, verified=True)
            db.commit()
            print(f"Administrator created: {user.email}")


if __name__ == "__main__":
    main()
