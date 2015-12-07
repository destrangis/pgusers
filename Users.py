
import os
import hashlib
import pickle

from Database import Database

OK = 0
NO_SUCH_USER = 1
EXPIRED = 2

class BadCallError(Exception):
	pass

class UserSpace(object):
	
	userspaces = {}    # instance list
	
	def __new__(cls, *args, **kwargs):
		'''Return the existing instance if already created or create a new one.
		'''
		dbname = kwargs.get("database", None)
		if dbname is None:
			raise BadCallError("database arg not specified. "
								"Use UserSpace(database=<name>)")
			
		if cls.userspaces.get(dbname, False):
			return cls.userspaces[dbname]
		else:
			newobj = super().__new__(cls)
			cls.userspaces[dbname] = newobj
			return newobj
			
			
	def __init__(self, **kwargs):
		self.dbname = kwargs.get("database", "NONAME")
		self.db = Database()
		self.connector = self.db.connect(**kwargs)
		dbinit(self.connector)	
	
	@staticmethod
	def xor_with_salt(strng, salt):
		lp = len(strng)
		ls = len(salt)
		ns = lp // ls + 1
		nsalt = salt * ns
		xorlist = []
		for c1, c2 in zip(nsalt, bytes(strng, "utf-8")):
			xorlist.append(c1 ^ c2)
		return bytes(xorlist)
		
	
	def create_user(self, username, password, email, extra_data=None):
		'''Create a user in the UserSpace's database.
		@param username	The username to be created, if there is already
		                a record with that username, a BadCallError is
		                raised.
		@param password The user's password in cleartext
		@param email	Email for notifications or password recovery.
						BadCallError is raised if the email exists in 
						the database.
		@param extra_data An application dependent dictionary to be stored
						as a pickle (e.g. phone number, password reminders,
						etc)
						
		@return Integer representing the user id
		'''
		salt = os.urandom(16)
		kpasswd = hashlib.md5(self.xor_with_salt(password, salt)).hexdigest()
		edata = pickle.dumps(extra_data)
		cr = self.connector.cursor()
		try:
			cr.execute("insert into users values (?, ?, ?, ?, ?, ?)",
						(None,
						 username,
						 email,
						 salt,
						 kpasswd,
						 edata) )
		except Exception as err:
			raise BadCallError(str(err))
		else:
			cr.execute("select userid from users where username = ?", (username,) )
			userid = cr.fetchone()[0]
		finally:
			self.connector.commit()
			cr.close()
		return userid
						 
		
	def validate_user(self, username, password):
		'''Validates (or logs in) a username.
		@param	username	The user's username
		@param 	password	The user's password in cleartext
		
		@return	Session key, as a string or empty string if not found 
				or wrong password.
		'''
		raise NotImplementedError
		
	def delete_user(self, username=None, userid=None):
		'''Delete a user given either its username or userid.
		
		Either username or userid must be specified.
		
		@param	username	The username (string)
		@param	userid		The userid (integer)
		
		@return OK if deleted, NO_SUCH_USER if not found.
		
		@throws BadCallError if neither username or userid are specified.
		'''
		query_stmt = "delete from users where {} = ?"
		if username is not None:
			query = query_stmt.format("username")
			value = username
		elif userid is not None:
			query = query_stmt.format("userid")
			value = userid
		else:
			raise BadCallError("delete_user(): Either 'username'"
			                 + " or 'userid' must be specified.")
			
		cr = self.connector.cursor()
		cr.execute(query, (value,))
		if cr.rowcount == 0:
			rc = NO_SUCH_USER
		else:
			rc = OK
		cr.close()
		return rc
		 
			
		
	def change_password(self, username, newpassword, oldpassword=None):
		'''Change a user's password
		@param	username	The username
		@param	newpassword	The new password
		@param	oldpassword	The current password
		
		If specified, oldpassword is checked against the current password
		and the call will fail if they don't match.
		If oldpassword is not specified, the password will be changed unconditionally.
		
		@returns OK or NO_SUCH_USER
		'''
		pass
		
	def check_key(self, key):
		'''Reset the session timeout.
		@param	key	The session key returned by validate_user()
		@returns	Tuple of the form (rc, username, userid)
					where rc is OK, NO_SUCH_USER or EXPIRED
					if NO_SUCH_USER or EXPIRED, username and userid will be None
					
		Resets the key's Time To Live to TIMEOUT
		'''
		pass
		
	def set_session_TTL(self, minutes):
		'''Sets the TTL for all sessions.
		@param	minutes	number of minutes of Time To Live.
		All sessions will be reset to this new TTL value.
		'''
		pass
		
	def find_user(self, username=None, email=None, userid=None):
		'''Find a user given either its username, its email or its userid.
		@param	username	The username string.
		@param	email		The email string.
		@param	userid		The userid (integer)
		@returns A dictionary with fields userid, username, email and extra_data
		         None if not found.
		'''
		query_stmt = ("select userid, username, email, extra_data "
		            + "from users where {} = ?")
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
			raise BadCallError("find_user(): Either 'username', "
			                 + "'email' or 'userid' must be specified.")

		cr = self.connector.cursor()
		cr.execute(query, (value,))
		
		row = cr.fetchone()
		if row is not None:
			ret_row = { d[0]: v for d, v in zip(cr.description, row) }
			ret_row["extra_data"] = pickle.loads(ret_row["extra_data"])
		else:
			ret_row = None
			
		cr.close()
		return ret_row
			
		

def dbm_select(connector_name):
	Database.install_connector(connector_name)
	
		
def dbinit(db):
	'''Create a new database structure
	'''		
	sql = [  # statements to be executed in sequence
	'''create table if not exists users (
			userid		integer primary key autoincrement,
			username	varchar(20) unique,
			email		varchar(128) unique,
			salt		varchar(16),
			kpasswd		varchar(32),
			extra_data	blob
			)
	''',
	'''create table if not exists sessions (
			userid	integer,
			key 	varchar(64),
			expiration integer
			)
	''',
	      ]

	for stmt in sql:
		db.execute(stmt)
	db.commit()
	return db
