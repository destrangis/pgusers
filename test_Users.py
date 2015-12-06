#! /usr/bin/env python3
import os
import unittest

import Users

class InitTests(unittest.TestCase):
	
	def tearDown(self):
		# this only works for the sqlite3 default connector
		while Users.UserSpace.userspaces:
			name, value = Users.UserSpace.userspaces.popitem()
			os.remove(name)
	
	def test_no_dbname_throws_exception(self):
		"Constructor w/o dbname throws exception"
		self.assertRaises(Users.BadCallError, Users.UserSpace)
		
	def test_constructor_new(self):
		"Constructor constructs"
		us = Users.UserSpace(database="testdb")
		self.assertIsNotNone(us)
		
	def test_constructor_existing(self):
		"Test that two instantiations with same dbname return same object"
		us0 = Users.UserSpace(database="test_new")
		us1 = Users.UserSpace(database="test_new")
		self.assertIs(us0, us1)
	
		
class UserTests(unittest.TestCase):
	
	def setUp(self):
		self.us = Users.UserSpace(database="user_tests0")
		
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
		self.assertRaises(Users.BadCallError,
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
		
	def test_find_user_needs_parameter(self):
		"find_user without one argument throws exception"
		self.assertRaises(Users.BadCallError, 
						self.us.find_user)
						
	def test_delete_nonexisting_user(self):
		"Delete non existing user returns NO_SUCH_USER"
		self.assertEqual(Users.NO_SUCH_USER, 
				self.us.delete_user(username="pedro"))
				
	def test_delete_existing_user(self):
		"Can't find a user after deleting it by username"
		userid = self.us.create_user("user4", "pass4", "user4@doesntexi.st")
		self.assertEqual(Users.OK, 
				self.us.delete_user(username="user4"))
		udata = self.us.find_user(userid=userid)
		self.assertIsNone(udata)
		
	def test_delete_existing_user_by_id(self):
		"Can't find a user after deleting it by username"
		userid = self.us.create_user("user5", "pass5", "user5@doesntexi.st")
		self.assertEqual(Users.OK, 
				self.us.delete_user(userid=userid))
		udata = self.us.find_user(userid=userid)
		self.assertIsNone(udata)
		
	def test_delete_throws_exception(self):
		"Delete throws exception if parameters missing"
		self.assertRaises(Users.BadCallError,
					self.us.delete_user)
					

class PasswordTests(unittest.TestCase):
	
	def setUp(self):
		self.us = Users.UserSpace(database="user_tests0")
		
	def tearDown(self):
		os.remove("user_tests0")
						
	def test_authenticate_good_password(self):
		"Can authenticate a user with good password"
		self.us.create_user("user6", "pass6", "user6@suchandsu.ch")						
		key = self.us.validate_user("user6", "pass6")
		self.assertEqual(type(key), bytes)
		self.assertTrue(key)
		
	def test_authenticate_bad_password(self):
		"Existing users with incorrect passwords are not authenticated"
		self.us.create_user("user7", "pass7", "user7@suchandsu.ch")	
		key = self.us.validate_user("user7", "badpass")
		self.assertFalse(key)
		
	def test_nonexisting_users_not_authenticated(self):
		"Nonexisting users are not authenticated"
		key = self.us.validate_user("idontexist", "pass")
		self.assertFalse(key)
		

if __name__ == "__main__":
	unittest.main()
