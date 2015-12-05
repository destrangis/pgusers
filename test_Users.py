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

if __name__ == "__main__":
	unittest.main()
