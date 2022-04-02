import sys
import argparse
import re
from datetime import datetime
from pprint import pprint
from getpass import getpass

import pgusers


def get_cli_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        default=False,
        help="print the module version and exit",
    )
    parser.add_argument(
        "--dbuser", "-u", metavar="DBUSER", help="PostgreSQL database user"
    )
    parser.add_argument(
        "--dbpasswd", "-p", metavar="PASSWD", help="password for the PostgreSQL user"
    )
    parser.add_argument(
        "--dbhost", "-s", metavar="HOST", help="hostname for the PostgreSQL database"
    )
    parser.add_argument(
        "--dbport",
        "-t",
        metavar="PORT",
        default="5432",
        help="port for the PostgreSQL database",
    )

    parser.add_argument("userspace", help="specify the userspace to work with")

    subparsers = parser.add_subparsers(title="subcommands", dest="cmd")

    adduser = subparsers.add_parser(
        "adduser",
        description="add a new user",
        help="add new user by specifying its userid, email and password",
    )
    adduser.add_argument(
        "--admin",
        "-a",
        action="store_true",
        default=False,
        help="make the new user an admin user",
    )
    adduser.add_argument("email", help="The user's email")
    adduser.add_argument(
        "userid", nargs="?", help="The user id, if different than the email"
    )

    setadmin = subparsers.add_parser(
        "setadmin",
        description="change the privileges of a user",
        help="add or remove adminstrator privileges to a user",
    )
    setadmin.add_argument(
        "--remove",
        "-r",
        action="store_true",
        default=False,
        help="demote an administrator to regular user",
    )
    setadmin.add_argument("user", help="userid or email for the user")

    cpasswd = subparsers.add_parser(
        "cpasswd",
        description="change the password for a user",
        help="change the password for a user",
    )
    cpasswd.add_argument("user", help="userid or email for the user")

    deluser = subparsers.add_parser(
        "delete", description="delete a user", help="delete a user"
    )
    deluser.add_argument("user", help="userid or email for the user")

    subparsers.add_parser("list", description="list all users", help="list all users")

    info = subparsers.add_parser(
        "info",
        description="print information about one user",
        help="print information about one user",
    )
    info.add_argument("user", help="userid or email for the user")

    listsess = subparsers.add_parser(
        "listsessions",
        description="list the sessions of a user (or all the users)",
        help="list the sessions of a user (or all the users)",
    )
    listsess.add_argument(
        "--all",
        "-a",
        action="store_true",
        default=False,
        help="list the sessions of all the users",
    )
    listsess.add_argument(
        "--expired",
        "-x",
        action="store_true",
        default=False,
        help="list only the sessions that have expired",
    )
    listsess.add_argument("user", nargs="?", help="userid or email for the user")

    killsess = subparsers.add_parser(
        "killsessions",
        description="kill the sessions of a user (or all the users)",
        help="kill the sessions of a user (or all the users)",
    )
    killsess.add_argument(
        "--all",
        "-a",
        action="store_true",
        default=False,
        help="kill the sessions of all the users",
    )
    killsess.add_argument(
        "--expired",
        "-x",
        action="store_true",
        default=False,
        help="kill only the sessions that have expired",
    )
    killsess.add_argument("user", nargs="?", help="userid or email for the user")

    return parser.parse_args(argv)


def get_userspace(opts):
    name = opts.userspace
    params = {}
    if opts.dbuser:
        params["user"] = opts.dbuser
    if opts.dbpasswd:
        params["password"] = opts.dbpasswd
    if opts.dbhost:
        params["host"] = opts.dbhost
    if opts.dbhost or opts.dbport != "5432":  # don't bother with port if no host
        params["port"] = opts.dbport

    return pgusers.UserSpace(name, **params)


def enter_password(userid):
    match = False
    tries = 0
    while not match and tries < 3:
        tries += 1
        pwd1 = getpass(f"Enter password for {userid}: ")
        pwd2 = getpass(f"Repeat password for {userid}: ")
        if pwd1 == pwd2:
            return pwd1
        else:
            print("Passwords don't match.\n")

    raise RuntimeError("Too many retries")


def find_user(userspace, user):
    udata = userspace.find_user(username=user)
    if udata is None:
        udata = userspace.find_user(email=user)
    if udata is None:
        return None
    return udata


def cmd_adduser(opts):
    eml_ptn = r"[\w.-]+@[\w.-]+\.\w+"
    email = opts.email
    userid = opts.userid if opts.userid else opts.email
    if not re.match(eml_ptn, email):
        print(f"Not a valid emai address: '{email}'")
        return 1
    userspace = get_userspace(opts)

    try:
        password = enter_password(userid)
    except RuntimeError:
        print("Too many retries. Exiting.")
        return 1

    uid = userspace.create_user(userid, password, email, opts.admin, None)
    print(f"User '{userid}' created with uid: {uid}")
    return 0


def cmd_cpassword(opts):
    userspace = get_userspace(opts)
    user = find_user(userspace, opts.user)
    if user is None:
        print(f"User '{opts.user}' not found.")
        return 1

    try:
        password = enter_password(user["username"])
    except RuntimeError:
        print("Too many retries. Exiting.")
        return 1

    userspace.change_password(user["userid"], password)
    print(f"Password changed for '{opts.user}'")
    return 0


def cmd_delete(opts):
    userspace = get_userspace(opts)
    user = find_user(userspace, opts.user)
    if user is None:
        print(f"User '{opts.user}' not found.")
        return 1
    userspace.delete_user(userid=user["userid"])
    print(f"User '{user['username']}' deleted.")


def cmd_listusers(opts):
    userspace = get_userspace(opts)
    for i, (uid, username, email, admin) in enumerate(userspace.all_users()):
        if i == 0:
            print(f"{'uid':5}|{'username':20}|adm|{'email':30}")
            print(f"{'='*5}+{'='*20}+===+{'='*30}")
        print(f"{uid:5}|{username:20}|{'yes' if admin else ' ':3}|{email:30}")
    return 0


def cmd_info(opts):
    userspace = get_userspace(opts)
    user = find_user(userspace, opts.user)
    pprint(user)
    return 0


def cmd_killsessions(opts):
    if opts.user and opts.all:
        print("A user cannot be specified with --all option.")
        return 1

    userspace = get_userspace(opts)
    if opts.all:
        uid = 0
    elif opts.user:
        user = find_user(userspace, opts.user)
        uid = user["userid"]
    else:
        print("Eithe user or --all must be specified")
        return 1

    userspace.kill_sessions(uid, opts.expired)
    return 0


def cmd_listsessions(opts):
    if opts.user and opts.all:
        print("A user cannot be specified with --all option.")
        return 1

    userspace = get_userspace(opts)
    if opts.all:
        uid = 0
    elif opts.user:
        user = find_user(userspace, opts.user)
        uid = user["userid"]
    else:
        print("Eithe user or --all must be specified")
        return 1

    for i, (username, key, expiration) in enumerate(
        userspace.list_sessions(uid, opts.expired)
    ):
        if i == 0:
            print(f"{'user':10}|{'key':32}|{'expiration':30}")
            print(f"{'='*10}+{'='*32}+{'='*30}")
        exp = datetime.fromtimestamp(expiration).strftime("%H:%M:%S.%f %d/%m/%Y")
        print(f"{username:10}|{key:32}|{exp:30}")

    return 0


def cmd_setadmin(opts):
    admin = not opts.remove
    userspace = get_userspace(opts)
    user = find_user(userspace, opts.user)
    if not user:
        print(f"{opts.user} not found.")
        return 1

    userspace.set_admin(user["userid"], admin)
    print(f"{user['username']} is now {'an admin' if admin else 'a regular user'}")
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    opts = get_cli_options(argv)

    if opts.version:
        print(f"pgusers {pgusers.version}")
        return 0

    commands = {
        "adduser": cmd_adduser,
        "cpasswd": cmd_cpassword,
        "setadmin": cmd_setadmin,
        "delete": cmd_delete,
        "list": cmd_listusers,
        "info": cmd_info,
        "listsessions": cmd_listsessions,
        "killsessions": cmd_killsessions,
    }
    return commands[opts.cmd](opts)


if __name__ == "__main__":
    sys.exit(main())
