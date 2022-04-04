import os
import hashlib
import pickle
import binascii
import time

import psycopg2

OK = 0
NOT_FOUND = 1
EXPIRED = 2
REJECTED = 3


class BadCallError(Exception):
    pass


class UserSpace:

    userspaces = {}  # instance list
    ttl = 864000.0  # 10 day default session time to live

    def __new__(cls, dbname="", **kwargs):
        """Return the existing instance if already created or create a new one."""
        if not dbname:
            raise BadCallError("No name for UserSpace")

        if cls.userspaces.get(dbname, False):
            return cls.userspaces[dbname]
        else:
            newobj = super().__new__(cls)
            cls.userspaces[dbname] = newobj
            return newobj

    def __init__(self, dbname="", **kwargs):
        self.connector = psycopg2.connect(dbname=dbname, **kwargs)
        dbinit(self.connector)

    def create_user(self, username, password, email, admin=False, extra_data=None):
        """Create a user in the UserSpace's database.
        @param username The username to be created, if there is already
                        a record with that username, a BadCallError is
                        raised.
        @param password The user's password in cleartext
        @param email    Email for notifications or password recovery.
                        BadCallError is raised if the email exists in
                        the database.
        @param admin    Whether the user is an admin.
        @param extra_data An application dependent dictionary to be stored
                        as a pickle (e.g. phone number, password reminders,
                        etc)

        @return Integer representing the user id
        """
        sql_retrieve_username = "select userid from users where username = %s"
        cr = self.connector.cursor()
        cr.execute(sql_retrieve_username, (username,))
        if cr.fetchone():
            raise BadCallError(f"User '{username}' already in database")
        salt = os.urandom(16)
        bpwd = password.encode("utf-8")
        kpasswd = hashlib.pbkdf2_hmac("sha512", bpwd, salt, 100000)
        edata = pickle.dumps(extra_data)
        try:
            cr.execute(
                "insert into users (username, email, salt, kpasswd, admin, extra_data) "
                "values (%s, %s, %s, %s, %s, %s)",
                (username, email, salt.hex(), kpasswd.hex(), admin, edata),
            )
        except Exception as err:
            raise BadCallError(str(err))
        else:
            cr.execute(sql_retrieve_username, (username,))
            userid = cr.fetchone()[0]
        finally:
            self.connector.commit()
            cr.close()
        return userid

    def is_admin(self, userid):
        """
        True if a user is admin
        @param userid   The user id as returned by find_user()
        @return True if the user is admin, False otherwise
        """
        with self.connector.cursor() as cr:
            cr.execute("select admin from users where userid = %s", (userid,))
            result = list(cr.fetchall())
            self.connector.commit()
            if result:
                return result[0][0]
            else:
                raise BadCallError("User {} not found.".format(userid))

    def set_admin(self, userid, admin=True):
        """
        Mark the user as admin
        """
        admin = True if admin else False  # force a truthy or falsey value to boolean
        with self.connector.cursor() as cr:
            cr.execute("update users set admin = %s where userid = %s", (admin, userid))
            self.connector.commit()

    def validate_user(self, username, password, extra_data=None):
        """Validates (or logs in) a username.
        @param  username    The user's username
        @param  password    The user's password in cleartext
        @param  extra_data  Dictionary with additional, user defined
                            data about the session.

        @return tuple(key, admin, userid)
                        key is a string or empty string if not found
                        or wrong password; userid is the user id as
                        returned by create_user()
        """
        cr = self.connector.cursor()
        cr.execute(
            "select userid, username, salt, kpasswd, admin "
            "from users where username = %s",
            (username,),
        )
        assert cr.rowcount <= 1
        row = cr.fetchone()
        cr.close()
        self.connector.commit()
        if row is None:
            return "", False, None
        userid, username, salt, kpasswd, admin = row
        bpwd = bytes(password, "utf-8")
        hpwd = hashlib.pbkdf2_hmac("sha512", bpwd, binascii.unhexlify(salt), 100000)
        if binascii.unhexlify(kpasswd) == hpwd:
            return self._make_session_key(userid, extra_data), admin, userid
        else:
            return "", False, None

    def _make_session_key(self, userid, extra_data):
        now = time.time()
        timeout = self.ttl + now
        sessid = hashlib.md5(bytes(str(userid) + str(now), "utf-8")).hexdigest()
        # xsessid = binascii.hexlify(sessid).decode("utf-8")
        cr = self.connector.cursor()
        cr.execute(
            "insert into sessions values (%s, %s, %s, %s)",
            (userid, sessid, timeout, pickle.dumps(extra_data)),
        )
        self.connector.commit()
        cr.close()
        return sessid

    def delete_user(self, username=None, userid=None):
        """Delete a user given either its username or userid.

        Either username or userid must be specified.

        @param  username    The username (string)
        @param  userid      The userid (integer)

        @return OK if deleted, NOT_FOUND if not found.

        @throws BadCallError if neither username or userid are specified.
        """
        query_stmt = "delete from users where {} = %s"
        if username is not None:
            query = query_stmt.format("username")
            value = username
        elif userid is not None:
            query = query_stmt.format("userid")
            value = userid
        else:
            raise BadCallError(
                "delete_user(): Either 'username'" + " or 'userid' must be specified."
            )

        cr = self.connector.cursor()
        cr.execute(query, (value,))
        if cr.rowcount == 0:
            rc = NOT_FOUND
        else:
            rc = OK
        cr.close()
        self.connector.commit()
        return rc

    def change_password(self, userid, newpassword, oldpassword=None):
        """Change a user's password
        @param  userid      The user id, as returned by create_user()
        @param  newpassword The new password
        @param  oldpassword The current password

        If specified, oldpassword is checked against the current password
        and the call will fail if they don't match.
        If oldpassword is not specified, the password will be changed unconditionally.

        @returns OK, NOT_FOUND or REJECTED
        """
        cr = self.connector.cursor()
        cr.execute("select username from users where userid = %s", (userid,))
        row = cr.fetchone()
        if row is None:
            cr.close()
            return NOT_FOUND
        username = row[0]

        if oldpassword is not None:
            key, admin, uid = self.validate_user(username, oldpassword)
            if not key:
                return REJECTED
            self._kill_session(key)

        bpwd = bytes(newpassword, "utf-8")
        salt = os.urandom(16)
        hashpwd = hashlib.pbkdf2_hmac("sha512", bpwd, salt, 100000)
        cr.execute(
            "update users set kpasswd = %s, salt = %s where userid = %s",
            (hashpwd.hex(), salt.hex(), userid),
        )
        self.connector.commit()
        cr.close()
        return OK

    def _kill_session(self, key):
        cr = self.connector.cursor()
        cr.execute("delete from sessions where key = %s", (key,))
        self.connector.commit()
        cr.close()

    def check_key(self, key):
        """Reset the session timeout.
        @param  key The session key returned by validate_user()
        @returns    Tuple of the form (rc, username, userid, extra_data)
                    where rc is OK, NOT_FOUND or EXPIRED
                    if NOT_FOUND or EXPIRED, username and userid will be None

        Resets the key's Time To Live to TIMEOUT
        """
        cr = self.connector.cursor()
        cr.execute(
            """select t1.userid, t1.key, t1.expiration,
                             t1.extra_data, t2.username
            from sessions as t1, users as t2
            where  t1.userid = t2.userid and
                   t1.key = %s""",
            (key,),
        )
        session_row = cr.fetchone()
        if session_row is None:
            cr.close()
            return (NOT_FOUND, None, None, None)
        now = time.time()
        uid, key, timeout, extra, username = session_row
        extra_data = pickle.loads(extra)
        if timeout < now:
            cr.execute("delete from sessions where key = %s", (key,))
            self.connector.commit()
            cr.close()
            return (EXPIRED, None, None, None)

        timeout = now + self.ttl
        cr.execute(
            "update sessions set expiration = %s " "where key = %s", (timeout, key)
        )
        self.connector.commit()
        cr.close()
        return (OK, username, uid, extra_data)

    def set_session_TTL(self, secs):
        """Sets the TTL for all sessions.
        @param  secs    number of seconds of Time To Live.
        All new sessions or checked sessions will be set to this new TTL value.
        """
        self.ttl = secs

    def find_user(self, username=None, email=None, userid=None):
        """Find a user given either its username, its email or its userid.
        @param  username    The username string.
        @param  email       The email string.
        @param  userid      The userid (integer)
        @returns A dictionary with fields userid, username, email, admin, and extra_data
                 None if not found.
        """
        query_stmt = (
            "select userid, username, email, admin, extra_data "
            "from users where {} = %s"
        )
        if username is not None:
            query = query_stmt.format("username")
            value = username
        elif email is not None:
            query = query_stmt.format("email")
            value = email
        elif userid is not None:
            query = query_stmt.format("userid")
            value = userid
        else:
            raise BadCallError(
                "find_user(): Either 'username', "
                "'email' or 'userid' must be specified."
            )

        cr = self.connector.cursor()
        cr.execute(query, (value,))

        row = cr.fetchone()
        if row is not None:
            ret_row = {d[0]: v for d, v in zip(cr.description, row)}
            ret_row["extra_data"] = pickle.loads(ret_row["extra_data"])
        else:
            ret_row = None

        cr.close()
        self.connector.commit()
        return ret_row

    def modify_user(self, userid, username=None, email=None, extra_data=None):
        """Modify user data.
        @param userid   The user id as returned by create_user()
        @param username The new username to change, if specified.
        @param email    The new email to change, if specified.
        @param extra_data The new extra_data to change, if specified.

        @returns OK if successful NOT_FOUND if not.
        """
        rc = OK
        fields_sql = []
        fields_list = []
        if username is not None:
            fields_sql.append("username = %s")
            fields_list.append(username)
        if email is not None:
            fields_sql.append("email = %s")
            fields_list.append(email)
        if extra_data is not None:
            fields_sql.append("extra_data = %s")
            fields_list.append(pickle.dumps(extra_data))

        if fields_list:
            query = "update users set " + ", ".join(fields_sql) + " where userid = %s"

            fields_list.append(userid)

            cr = self.connector.cursor()
            cr.execute(query, fields_list)
            if cr.rowcount <= 0:
                rc = NOT_FOUND
            self.connector.commit()
            cr.close()

        return rc

    def all_users(self):
        """Generator yielding (userid, username, email, admin) tuples for all users"""
        with self.connector.cursor() as cr:
            cr.execute(
                "select userid, username, email, admin from users " "order by username"
            )
            for row in cr.fetchall():
                yield row
            self.connector.commit()

    def list_sessions(self, uid, expired=False):
        now = time.time()
        sql = """select u.username, s.key, s.expiration
                 from sessions s
                 inner join users u on (s.userid = u.userid) """
        args = []
        uidcond = ""
        if uid != 0:
            uidcond = "(s.userid = %s)"
            args.append(uid)
        expcond = ""
        if expired:
            expcond = "(s.expiration < %s)"
            args.append(now)

        if uidcond or expcond:
            sql += "where "
        if uidcond:
            sql += uidcond
        if uidcond and expcond:
            sql += " and "
        if expcond:
            sql += expcond

        with self.connector.cursor() as cr:
            cr.execute(sql, args)
            for row in cr.fetchall():
                yield row

        self.connector.commit()

    def kill_sessions(self, uid, expired=False):
        now = time.time()
        sql = "delete from sessions "
        args = []
        uidcond = ""
        if uid != 0:
            uidcond = "(userid = %s)"
            args.append(uid)
        expcond = ""
        if expired:
            expcond = "(expiration < %s)"
            args.append(now)

        if uidcond or expcond:
            sql += "where "
        if uidcond:
            sql += uidcond
        if uidcond and expcond:
            sql += " and "
        if expcond:
            sql += expcond

        with self.connector.cursor() as cr:
            cr.execute(sql, args)

        self.connector.commit()


def dbinit(db):
    """Create a new database structure"""
    sql = [  # statements to be executed in sequence
        """create table if not exists users (
            userid      serial primary key,
            username    varchar(20),
            email       varchar(128),
            salt        varchar(32),
            kpasswd     varchar(128),
            admin       boolean not null default 'no',
            extra_data  bytea
            )
    """,
        """create table if not exists sessions (
            userid  integer,
            key     varchar(32),
            expiration real,
            extra_data  bytea
            )
    """,
    ]
    csr = db.cursor()
    for stmt in sql:
        csr.execute(stmt)
    db.commit()
    return db
