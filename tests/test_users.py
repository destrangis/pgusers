#! /usr/bin/env python3
import unittest
import time
from unittest.mock import MagicMock

import pgusers as users

DBNAME = "pytestdb"


class InitTests(unittest.TestCase):

    # def tearDown(self):
    # this only works for the sqlite3 default connector
    # while users.UserSpace.userspaces:
    # name, value = users.UserSpace.userspaces.popitem()
    # os.remove(name)

    def test_no_dbname_throws_exception(self):
        "Constructor w/o dbname throws exception"
        self.assertRaises(users.BadCallError, users.UserSpace)

    def test_constructor_new(self):
        "Constructor constructs"
        us = users.UserSpace(DBNAME)
        self.assertIsNotNone(us)

    def test_constructor_existing(self):
        "Test that two instantiations with same dbname return same object"
        us0 = users.UserSpace(DBNAME)
        us1 = users.UserSpace(DBNAME)
        self.assertIs(us0, us1)


class UserTests(unittest.TestCase):
    def setUp(self):
        self.us = users.UserSpace(DBNAME)

    def tearDown(self):
        csr = self.us.connector.cursor()
        csr.execute("drop table if exists users")
        csr.execute("drop table if exists sessions")
        self.us.connector.commit()
        csr.close()

    def test_user_gets_added(self):
        "User gets added"
        self.assertEqual(
            type(self.us.create_user("user1", "pass1", "user1@something.com")), int
        )

    def test_duplicate_user_gives_exception(self):
        "Exception trying to create existing user"
        self.us.create_user("user2", "pass2", "user2@abc.de")
        self.assertRaises(
            users.BadCallError, self.us.create_user, "user2", "pass3", "user2@fgh.ij"
        )

    def test_user_is_found_by_id(self):
        "Can find a user by its userid"
        userid = self.us.create_user(
            "user3", "pass3", "user3@abc.de", extra_data={"data1": 543}
        )
        udata = self.us.find_user(userid=userid)
        self.assertIsNotNone(udata)
        self.assertEqual(udata["userid"], userid)
        self.assertEqual(udata["username"], "user3")
        self.assertEqual(udata["email"], "user3@abc.de")
        self.assertEqual(udata["extra_data"], {"data1": 543})

    def test_user_is_found_by_username(self):
        "Can find a user by its username"
        userid = self.us.create_user(
            "user3", "pass3", "user3@abc.de", extra_data={"data1": 543}
        )
        udata = self.us.find_user(username="user3")
        self.assertIsNotNone(udata)
        self.assertEqual(udata["userid"], userid)
        self.assertEqual(udata["username"], "user3")
        self.assertEqual(udata["email"], "user3@abc.de")
        self.assertEqual(udata["extra_data"], {"data1": 543})

    def test_user_is_found_by_email(self):
        "Can find a user by its email"
        userid = self.us.create_user(
            "user3", "pass3", "user3@abc.de", extra_data={"data1": 543}
        )
        udata = self.us.find_user(email="user3@abc.de")
        self.assertIsNotNone(udata)
        self.assertEqual(udata["userid"], userid)
        self.assertEqual(udata["username"], "user3")
        self.assertEqual(udata["email"], "user3@abc.de")
        self.assertEqual(udata["extra_data"], {"data1": 543})

    def test_nonexisting_users_not_found(self):
        "Search for nonexisting user returns None"
        udata = self.us.find_user(userid=5404)
        self.assertIsNone(udata)

    def test_find_user_needs_parameter(self):
        "find_user without one argument throws exception"
        self.assertRaises(users.BadCallError, self.us.find_user)

    def test_delete_nonexisting_user(self):
        "Delete non existing user returns NOT_FOUND"
        self.assertEqual(users.NOT_FOUND, self.us.delete_user(username="pedro"))

    def test_delete_existing_user(self):
        "Can't find a user after deleting it by username"
        userid = self.us.create_user("user4", "pass4", "user4@doesntexi.st")
        self.assertEqual(users.OK, self.us.delete_user(username="user4"))
        udata = self.us.find_user(userid=userid)
        self.assertIsNone(udata)

    def test_delete_existing_user_by_id(self):
        "Can't find a user after deleting it by username"
        userid = self.us.create_user("user5", "pass5", "user5@doesntexi.st")
        self.assertEqual(users.OK, self.us.delete_user(userid=userid))
        udata = self.us.find_user(userid=userid)
        self.assertIsNone(udata)

    def test_delete_throws_exception(self):
        "Delete throws exception if parameters missing"
        self.assertRaises(users.BadCallError, self.us.delete_user)

    def test_modify_user(self):
        "Can modify user data."
        userid = self.us.create_user(
            "user20", "pass20", "user20@doesntexi.st", extra_data={"name": "Dave"}
        )
        rc = self.us.modify_user(
            userid,
            username="user21",
            email="user21@somewhereel.se",
            extra_data={"name": "Henrietta", "age": 22},
        )
        self.assertEqual(rc, users.OK)
        userdata = self.us.find_user(userid=userid)
        self.assertEqual(userdata["username"], "user21")
        self.assertEqual(userdata["email"], "user21@somewhereel.se")
        self.assertEqual(userdata["extra_data"], {"name": "Henrietta", "age": 22})

    def test_modify_nonexisting_user(self):
        "Modify nonexisting user reports NOT_FOUND"
        userid = self.us.create_user(
            "user22", "pass22", "user22@doesntexi.st", extra_data={"name": "Henrietta"}
        )
        self.assertEqual(users.OK, self.us.delete_user(userid=userid))
        rc = self.us.modify_user(
            userid,
            username="user23",
            email="user23@somewhereel.se",
            extra_data={"name": "Abelard", "age": 82},
        )
        self.assertEqual(rc, users.NOT_FOUND)

    def test_all_users(self):
        "all_users() returns all users"
        usrlst = [
            ("henrietta", "henrietta@hi.com", False),
            ("root", "admin@bigboss.com", True),
            ("bob", "bob@bebop.com", False),
        ]
        expected = [
            (3, "bob", "bob@bebop.com", False),
            (1, "henrietta", "henrietta@hi.com", False),
            (2, "root", "admin@bigboss.com", True),
        ]
        for user, email, admin in usrlst:
            self.us.create_user(user, "adssdas", email, admin)

        for exp, retr in zip(expected, self.us.all_users()):
            self.assertEqual(exp, retr)

    def test_all_users_on_empty_db(self):
        "all_users() on empty db returns no users"
        self.assertEqual([], list(self.us.all_users()))

    def test_retrieve_admin_user(self):
        "an admin user is retrieved"
        uid = self.us.create_user("user1", "pw1", "user@somewhere.com", True)
        self.assertTrue(self.us.is_admin(uid))

    def test_retrieve_nonadmin_user(self):
        "a non-admin user is retrieved"
        uid = self.us.create_user("user1", "pw1", "user@somewhere.com", False)
        self.assertFalse(self.us.is_admin(uid))

    def test_normal_user_becomes_admin(self):
        "a non-admin user can be set as admin"
        uid = self.us.create_user("user1", "pw1", "user@somewhere.com", False)
        self.us.set_admin(uid)
        self.assertTrue(self.us.is_admin(uid))

    def test_admin_user_becomes_unprivileged(self):
        "an admin user can be demoted to regular"
        uid = self.us.create_user("user1", "pw1", "user@somewhere.com", True)
        self.assertTrue(self.us.is_admin(uid))
        self.us.set_admin(uid, False)
        self.assertFalse(self.us.is_admin(uid))


class PasswordTests(unittest.TestCase):
    def setUp(self):
        self.us = users.UserSpace(DBNAME)

    def tearDown(self):
        csr = self.us.connector.cursor()
        csr.execute("drop table if exists users")
        csr.execute("drop table if exists sessions")
        self.us.connector.commit()
        csr.close()

    def test_authenticate_good_password(self):
        "Can authenticate a user with good password"
        userid = self.us.create_user("user6", "pass6", "user6@suchandsu.ch")
        key, armin, uid = self.us.validate_user("user6", "pass6")
        self.assertEqual(type(key), str)
        self.assertTrue(key)
        self.assertEqual(uid, userid)

    def test_authenticate_bad_password(self):
        "Existing users with incorrect passwords are not authenticated"
        self.us.create_user("user7", "pass7", "user7@suchandsu.ch")
        key, admin, uid = self.us.validate_user("user7", "badpass")
        self.assertFalse(key)
        self.assertIsNone(uid)

    def test_nonexisting_users_not_authenticated(self):
        "Nonexisting users are not authenticated"
        key, admin, uid = self.us.validate_user("idontexist", "pass")
        self.assertFalse(key)
        self.assertIsNone(uid)

    def test_change_password_with_oldpassword(self):
        "Unprivileged change password can be changed"
        uid = self.us.create_user("user8", "pass8", "user8@suchandsu.ch")
        rc = self.us.change_password(uid, "pass8888", "pass8")
        self.assertEqual(rc, users.OK)

    def test_change_password_with_bad_oldpassword(self):
        "Unprivileged change password rejected if bad oldpassword"
        uid = self.us.create_user("user8", "pass8", "user8@suchandsu.ch")
        rc = self.us.change_password(uid, "pass8888", "pass9")
        self.assertEqual(rc, users.REJECTED)

    def test_change_password(self):
        "Privileged change password works"
        uid = self.us.create_user("user9", "pass9", "user9@suchandsu.ch")
        rc = self.us.change_password(uid, "pass99999")
        self.assertEqual(rc, users.OK)

    def test_change_password_nonexisting_user(self):
        "Can't change password to nonexisting user"
        uid = 45343
        rc = self.us.change_password(uid, "pass10")
        self.assertEqual(rc, users.NOT_FOUND)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.us = users.UserSpace(DBNAME)

    def tearDown(self):
        csr = self.us.connector.cursor()
        csr.execute("drop table if exists users")
        csr.execute("drop table if exists sessions")
        self.us.connector.commit()
        csr.close()

    def test_session_gets_updated(self):
        "A validated session gets updated"
        userid = self.us.create_user("user10", "pass10", "user10@suchandsu.ch")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        seskey, admin, userid = self.us.validate_user("user10", "pass10")
        # at this point expiration time is 200.0+self.ttl

        # set the time at ttl - 1 minute
        time.time.return_value = 200.0 + self.us.ttl - 60.0
        rc, uname, uid, xtra = self.us.check_key(seskey)
        self.assertEqual(rc, users.OK)
        self.assertEqual(uname, "user10")
        self.assertEqual(uid, userid)
        self.assertIsNone(xtra)

        # set eht time at 1 min after ttl. It should have been renewed.
        time.time.return_value = 200.0 + self.us.ttl + 60.0
        rc, uname, uid, xtra = self.us.check_key(seskey)
        self.assertEqual(rc, users.OK)
        self.assertEqual(uname, "user10")
        self.assertEqual(uid, userid)
        self.assertIsNone(xtra)

        time.time = time_time

    def test_session_expires(self):
        "Sessions expire after their time to live"
        userid = self.us.create_user("user11", "pass11", "user11@suchandsu.ch")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        seskey, admin, userid = self.us.validate_user("user11", "pass11")

        # set time 1 minute after expiration
        time.time.return_value = 200.0 + self.us.ttl + 60.0
        rc, uname, uid, xtra = self.us.check_key(seskey)
        self.assertEqual(rc, users.EXPIRED)
        self.assertIsNone(uname)
        self.assertIsNone(uid)
        self.assertIsNone(xtra)

        time.time = time_time

    def test_recover_session_xtradata(self):
        self.us.create_user("user12", "pass12", "user12@all.net")
        seskey, admin, userid = self.us.validate_user(
            "user12", "pass12", {"ip": "195.16.159.2"}
        )
        rc, uname, uid, xtra = self.us.check_key(seskey)
        self.assertEqual(uname, "user12")
        self.assertEqual(xtra, {"ip": "195.16.159.2"})

    def test_list_all_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        k14, admin14, u14 = self.us.validate_user("user14", "pass14")
        k13, admin13, u13 = self.us.validate_user("user13", "pass13")

        sessdict = {}
        for user, key, expires in self.us.list_sessions(0):
            sessdict[user] = (key, expires)

        self.assertEqual(2, len(sessdict))
        self.assertTrue("user14" in sessdict)
        self.assertEqual(k14, sessdict["user14"][0])
        self.assertTrue("user13" in sessdict)
        self.assertEqual(k13, sessdict["user13"][0])

    def test_list_all_expired_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        k14, admin14, u14 = self.us.validate_user("user14", "pass14")
        time.time.return_value = 500.0
        k13, admin13, u13 = self.us.validate_user("user13", "pass13")
        # set time after user14's session expiration but not user13's
        time.time.return_value = 200.0 + self.us.ttl + 60.0

        sessdict = {}
        for user, key, expires in self.us.list_sessions(0, True):
            sessdict[user] = (key, expires)

        self.assertEqual(1, len(sessdict))
        self.assertTrue("user14" in sessdict)
        self.assertEqual(k14, sessdict["user14"][0])

        time.time = time_time

    def test_list_no_expired_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        self.us.validate_user("user14", "pass14")
        self.us.validate_user("user13", "pass13")

        self.assertEqual([], list(self.us.list_sessions(0, True)))

    def test_list_users_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        u14 = self.us.create_user("user14", "pass14", "user14@choff.com")
        k14, admin14, u14 = self.us.validate_user("user14", "pass14")
        self.us.validate_user("user13", "pass13")

        sessdict = {}
        for user, key, expires in self.us.list_sessions(u14):
            sessdict[user] = (key, expires)

        self.assertEqual(1, len(sessdict))
        self.assertTrue("user14" in sessdict)
        self.assertEqual(k14, sessdict["user14"][0])

    def test_list_users_expired_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        k14, admin14, u14 = self.us.validate_user("user14", "pass14")
        time.time.return_value = 500.0
        k13, admin13, u13 = self.us.validate_user("user13", "pass13")
        # set time after user14's session expiration but not user13's
        time.time.return_value = 200.0 + self.us.ttl + 60.0

        sessdict = {}
        for user, key, expires in self.us.list_sessions(u14, True):
            sessdict[user] = (key, expires)

        self.assertEqual(1, len(sessdict))
        self.assertTrue("user14" in sessdict)
        self.assertEqual(k14, sessdict["user14"][0])

        time.time = time_time

    def test_kill_all_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        self.us.validate_user("user14", "pass14")
        self.us.validate_user("user13", "pass13")

        self.us.kill_sessions(0)
        self.assertEqual([], list(self.us.list_sessions(0)))

    def test_kill_sessions_no_sessions(self):
        "kill_sessions() with no sessions does nothing"
        self.us.kill_sessions(0)
        self.assertEqual([], list(self.us.list_sessions(0)))

    def test_kill_all_expired_sessions(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        k14, admin14, u14 = self.us.validate_user("user14", "pass14")
        time.time.return_value = 500.0
        k13, admin13, u13 = self.us.validate_user("user13", "pass13")
        # set time after user14's session expiration but not user13's
        time.time.return_value = 200.0 + self.us.ttl + 60.0

        self.us.kill_sessions(0, True)
        sessdict = {}
        for user, key, expires in self.us.list_sessions(0):
            sessdict[user] = (key, expires)

        self.assertEqual(1, len(sessdict))
        self.assertTrue("user13" in sessdict)
        self.assertEqual(k13, sessdict["user13"][0])

        time.time = time_time

    def test_kill_all_sessions_of_user(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        u14 = self.us.create_user("user14", "pass14", "user14@choff.com")
        self.us.validate_user("user14", "pass14")
        k13, admin13, u13 = self.us.validate_user("user13", "pass13")
        self.us.validate_user("user14", "pass14")

        self.us.kill_sessions(u14)
        sessdict = {
            user: (key, expires) for user, key, expires in self.us.list_sessions(0)
        }
        self.assertEqual(1, len(sessdict))
        self.assertTrue("user13" in sessdict)
        self.assertEqual(k13, sessdict["user13"][0])

    def test_kill_all_expired_sessions_of_user(self):
        self.us.create_user("user13", "pass13", "user13@blah.com")
        self.us.create_user("user14", "pass14", "user14@choff.com")
        time_time = time.time
        time.time = MagicMock(return_value=200.0)
        k14a, admin14, u14 = self.us.validate_user("user14", "pass14")
        time.time.return_value = 500.0
        k14b, admin14, u14 = self.us.validate_user("user14", "pass14")
        self.us.validate_user("user13", "pass13")
        # set time after the first user14's session expiration but not the second
        time.time.return_value = 200.0 + self.us.ttl + 60.0

        self.us.kill_sessions(u14, True)
        sessdict = {}
        for user, key, expires in self.us.list_sessions(u14):
            sessdict[user] = (key, expires)

        self.assertEqual(1, len(sessdict))
        self.assertTrue("user14" in sessdict)
        self.assertEqual(k14b, sessdict["user14"][0])

        time.time = time_time


if __name__ == "__main__":
    unittest.main()
