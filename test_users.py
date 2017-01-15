#! /usr/bin/env python3
import os
import sys
import unittest
import time
from unittest.mock import MagicMock

sys.path.append("..") # so Python finds UserManagement in this directory
import UserManagement.users as users

class InitTests(unittest.TestCase):
	
	def tearDown(self):
		# this only works for the sqlite3 default connector
		while users.UserSpace.userspaces:
			name, value = users.UserSpace.userspaces.popitem()
			os.remove(name)
	
	def test_no_dbname_throws_exception(self):
		"Constructor w/o dbname throws exception"
		self.assertRaises(users.BadCallError, users.UserSpace)
		
	def test_constructor_new(self):
		"Constructor constructs"
		us = users.UserSpace(database="testdb")
		self.assertIsNotNone(us)
		
	def test_constructor_existing(self):
		"Test that two instantiations with same dbname return same object"
		us0 = users.UserSpace(database="test_new")
		us1 = users.UserSpace(database="test_new")
		self.assertIs(us0, us1)
	
		
class UserTests(unittest.TestCase):
	
	def setUp(self):
		self.us = users.UserSpace(database="user_tests0")
		
	def tearDown(self):
		os.remove("user_tests0")
	
	def test_user_gets_added(self):
		"User gets added"
		self.assertEqual(type(self.us.create_user("user1", "pass1", 
												"user1@something.com")),
						int)
						
	def test_duplicate_user_gives_exception(self):
		"Exception trying to create existing user"
		self.us.create_user("user2", "pass2", "user2@abc.de")
		self.assertRaises(users.BadCallError,
						self.us.create_user, "user2", "pass3", "user2@fgh.ij")
	
	def test_user_is_found_by_id(self):
		"Can find a user by its userid"
		userid = self.us.create_user("user3", "pass3", "user3@abc.de", 
						extra_data={"data1": 543})
		udata = self.us.find_user(userid=userid)
		self.assertIsNotNone(udata)
		self.assertEqual(udata["userid"], userid)
		self.assertEqual(udata["username"], "user3")
		self.assertEqual(udata["email"], "user3@abc.de")
		self.assertEqual(udata["extra_data"], {"data1":543})
		
	def test_user_is_found_by_username(self):
		"Can find a user by its username"
		userid = self.us.create_user("user3", "pass3", "user3@abc.de", 
						extra_data={"data1": 543})
		udata = self.us.find_user(username="user3")
		self.assertIsNotNone(udata)
		self.assertEqual(udata["userid"], userid)
		self.assertEqual(udata["username"], "user3")
		self.assertEqual(udata["email"], "user3@abc.de")
		self.assertEqual(udata["extra_data"], {"data1":543})	
		
	def test_user_is_found_by_email(self):
		"Can find a user by its email"
		userid = self.us.create_user("user3", "pass3", "user3@abc.de", 
						extra_data={"data1": 543})
		udata = self.us.find_user(email="user3@abc.de")
		self.assertIsNotNone(udata)
		self.assertEqual(udata["userid"], userid)
		self.assertEqual(udata["username"], "user3")
		self.assertEqual(udata["email"], "user3@abc.de")
		self.assertEqual(udata["extra_data"], {"data1":543})
		
	def test_nonexisting_users_not_found(self):
		"Search for nonexisting user returns None"
		udata = self.us.find_user(userid=5404)
		self.assertIsNone(udata)
		
	def test_find_user_needs_parameter(self):
		"find_user without one argument throws exception"
		self.assertRaises(users.BadCallError, 
						self.us.find_user)
						
	def test_delete_nonexisting_user(self):
		"Delete non existing user returns NOT_FOUND"
		self.assertEqual(users.NOT_FOUND, 
				self.us.delete_user(username="pedro"))
				
	def test_delete_existing_user(self):
		"Can't find a user after deleting it by username"
		userid = self.us.create_user("user4", "pass4", "user4@doesntexi.st")
		self.assertEqual(users.OK, 
				self.us.delete_user(username="user4"))
		udata = self.us.find_user(userid=userid)
		self.assertIsNone(udata)
		
	def test_delete_existing_user_by_id(self):
		"Can't find a user after deleting it by username"
		userid = self.us.create_user("user5", "pass5", "user5@doesntexi.st")
		self.assertEqual(users.OK, 
				self.us.delete_user(userid=userid))
		udata = self.us.find_user(userid=userid)
		self.assertIsNone(udata)
		
	def test_delete_throws_exception(self):
		"Delete throws exception if parameters missing"
		self.assertRaises(users.BadCallError,
					self.us.delete_user)
					
	def test_modify_user(self):
		"Can modify user data."
		userid = self.us.create_user("user20", "pass20", 
									"user20@doesntexi.st", 
									{"name": "Dave"})
		rc = self.us.modify_user(userid,
							username="user21",
							email="user21@somewhereel.se",
							extra_data={"name": "Henrietta",
							            "age": 22})
		self.assertEqual(rc, users.OK)
		userdata = self.us.find_user(userid=userid)
		self.assertEqual(userdata["username"], "user21")
		self.assertEqual(userdata["email"], "user21@somewhereel.se")
		self.assertEqual(userdata["extra_data"],
		                      {"name": "Henrietta",
							   "age": 22})
							   
	def test_modify_nonexisting_user(self):
		"Modify nonexisting user reports NOT_FOUND"
		userid = self.us.create_user("user22", "pass22", 
									"user22@doesntexi.st", 
									{"name": "Henrietta"})
		self.assertEqual(users.OK, self.us.delete_user(userid=userid))							
		rc = self.us.modify_user(userid,
							username="user23",
							email="user23@somewhereel.se",
							extra_data={"name": "Abelard",
										"age": 82})
		self.assertEqual(rc, users.NOT_FOUND)


class PasswordTests(unittest.TestCase):
	
	def setUp(self):
		self.us = users.UserSpace(database="user_tests0")
		
	def tearDown(self):
		os.remove("user_tests0")
						
	def test_authenticate_good_password(self):
		"Can authenticate a user with good password"
		userid = self.us.create_user("user6", "pass6", "user6@suchandsu.ch")						
		key, uid = self.us.validate_user("user6", "pass6")
		self.assertEqual(type(key), bytes)
		self.assertTrue(key)
		self.assertEqual(uid, userid)
		
	def test_authenticate_bad_password(self):
		"Existing users with incorrect passwords are not authenticated"
		self.us.create_user("user7", "pass7", "user7@suchandsu.ch")	
		key, uid = self.us.validate_user("user7", "badpass")
		self.assertFalse(key)
		self.assertIsNone(uid)
		
	def test_nonexisting_users_not_authenticated(self):
		"Nonexisting users are not authenticated"
		key, uid = self.us.validate_user("idontexist", "pass")
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
				
	def test_session_gets_updated(self):
		"A validated session gets updated"
		#import pdb; pdb.set_trace()
		userid = self.us.create_user("user10", "pass10", "user10@suchandsu.ch")
		time_time = time.time
		time.time = MagicMock(return_value=200.0)
		seskey, userid = self.us.validate_user("user10", "pass10")
		#at this point expiration time is 200.0+self.ttl
		
		# set the time at ttl - 1 minute
		time.time.return_value = 200.0 + self.us.ttl - 60.0
		rc, uname, uid, xtra = self.us.check_key(seskey)
		self.assertEqual(rc, users.OK)
		self.assertEqual(uname, "user10")
		self.assertEqual(uid, userid)
		self.assertIsNone(xtra)
		
		#set eht time at 1 min after ttl. It should have been renewed.
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
		seskey, userid = self.us.validate_user("user11", "pass11")
		
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
		seskey, userid = self.us.validate_user("user12", "pass12", 
									{"ip": "195.16.159.2"})
		rc, uname, uid, xtra = self.us.check_key(seskey)
		self.assertEqual(uname, "user12")
		self.assertEqual(xtra, {"ip": "195.16.159.2"})

if __name__ == "__main__":
	unittest.main()
