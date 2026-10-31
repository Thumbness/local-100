"""Manage who can sign in to the web app.

Run from the project root:
    python -m src.cli.users add alice --admin     create a user (or reset their password)
    python -m src.cli.users list
    python -m src.cli.users remove alice

Inside Docker: docker compose run --rm app python -m src.cli.users add alice --admin
Changes apply immediately; the server doesn't need a restart.
"""
import argparse
import getpass
import sys

from ..composition import user_directory
from ..domain.auth.user import normalize_username, password_problem, username_problem
from ..infrastructure.auth.passwords import WerkzeugPasswordHasher


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password: ")
    if first != getpass.getpass("Repeat password: "):
        raise SystemExit("The passwords don't match.")
    return first


def _add(args) -> None:
    directory = user_directory()
    name = normalize_username(args.username)
    problem = username_problem(name)
    if problem:
        raise SystemExit(problem)

    existing = directory.find(name)
    is_admin = args.admin if args.admin is not None else (existing.is_admin if existing else False)

    password = _read_password(args.password_stdin)
    problem = password_problem(password)
    if problem:
        raise SystemExit(problem)

    directory.add(name, WerkzeugPasswordHasher().hash(password), is_admin)
    print(f"{'Updated' if existing else 'Created'} user '{name}' ({'admin' if is_admin else 'member'}).")


def _list(_args) -> None:
    users = user_directory().usernames()
    if not users:
        print("No users yet. Add one with: python -m src.cli.users add NAME --admin")
    for user in users:
        print(f"{user.username:<24}{'admin' if user.is_admin else 'member'}")


def _remove(args) -> None:
    name = normalize_username(args.username)
    print(f"Removed '{name}'." if user_directory().remove(name) else f"No user named '{name}'.")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m src.cli.users", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="create a user, or reset their password")
    add.add_argument("username")
    role = add.add_mutually_exclusive_group()
    role.add_argument("--admin", dest="admin", action="store_true", default=None, help="may use the upload page")
    role.add_argument("--no-admin", dest="admin", action="store_false", help="remove admin rights")
    add.add_argument("--password-stdin", action="store_true", help="read the password from stdin (for scripts)")
    add.set_defaults(run=_add)

    commands.add_parser("list", help="show all users").set_defaults(run=_list)

    remove = commands.add_parser("remove", help="delete a user")
    remove.add_argument("username")
    remove.set_defaults(run=_remove)

    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
