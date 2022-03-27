import sys
import argparse
import re
from pprint import pprint
from getpass import getpass

import pgusers


def get_cli_options(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-v", action="store_true", default=False,
        help="print the module version and exit")
    parser.add_argument("--dbuser", "-u", metavar="DBUSER",
        help="PostgreSQL database user")
    parser.add_argument("--dbpasswd", "-p", metavar="PASSWD",
        help="password for the PostgreSQL user")
    parser.add_argument("--dbhost", "-s", metavar="HOST",
        help="hostname for the PostgreSQL database")
    parser.add_argument("--dbport", "-r",  metavar="PORT", default="5432",
        help="port for the PostgreSQL database")

    parser.add_argument("userspace",
        help="specify the userspace to work with")

    subparsers = parser.add_subparsers(title="subcommands", dest="cmd")

    adduser = subparsers.add_parser("adduser",
        description="add a new user",
        help="add new user by specifying its userid, email and password")
    adduser.add_argument("email",  help="The user's email")
    adduser.add_argument("userid", nargs="?", help="The user id, if different than the email")

    cpasswd = subparsers.add_parser("cpasswd",
        description="change the password for a user",
        help="change the password for a user")
    cpasswd.add_argument("user", help="userid or email for the user")

    deluser = subparsers.add_parser("delete",
        description="delete a user",
        help="delete a user")
    deluser.add_argument("user", help="userid or email for the user")

    listusers = subparsers.add_parser("list",
        description="list all users",
        help="list all users")

    info = subparsers.add_parser("info",
        description="print information about one user",
        help="print information about one user")
    info.add_argument("user", help="userid or email for the user")

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
    if opts.dbhost or opts.dbport != "5432": # don't bother with port if no host
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

    uid = userspace.create_user(userid, password, email, None)
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
    for i, (uid, username, email) in enumerate(userspace.all_users()):
        if i == 0:
            print(f"{'uid':5}|{'username':30}|{'email':30}")
            print(f"{'='*5}+{'='*30}+{'='*30}")
        print(f"{uid:5}|{username:30}|{email:30}")
    return 0

def cmd_info(opts):
    userspace = get_userspace(opts)
    user = find_user(userspace, opts.user)
    pprint(user)
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
        "delete": cmd_delete,
        "list": cmd_listusers,
        "info": cmd_info,
        }
    return commands[opts.cmd](opts)


if __name__ == "__main__":
    sys.exit(main())
