
import os
import hashlib
import pickle
import binascii
import time

from UserManagement.Database import Database

OK = 0
NOT_FOUND = 1
EXPIRED = 2
REJECTED = 3

__version__ = (0, 0, 3)
version     = "{0}.{1}.{2}".format(*__version__)

class BadCallError(Exception):
	pass

class UserSpace(object):
	
	userspaces = {}     # instance list
	ttl = 3600.0        # time in seconds before a session times out
		
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
		_dbinit(self.connector)	
	
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
		bpwd = bytes(password, "utf-8")
		kpasswd = hashlib.pbkdf2_hmac("sha512", bpwd, salt, 100000)
		edata = pickle.dumps(extra_data)
		cr = self.connector.cursor()
		try:
			cr.execute("insert into users values (?, ?, ?, ?, ?, ?)",
						(None,
						 username,
						 email,
						 binascii.hexlify(salt),
						 binascii.hexlify(kpasswd),
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
						 
		
	def validate_user(self, username, password, extra_data=None):
		'''Validates (or logs in) a username.
		@param	username	The user's username
		@param 	password	The user's password in cleartext
		@param	extra_data	Dictionary with additional, user defined 
							data about the session.
		
		@return	tuple(key, userid)
						key is a string or empty string if not found 
				        or wrong password; userid is the user id as 
				        returned by create_user()
		'''
		cr = self.connector.cursor()
		cr.execute("""select userid, username, salt, kpasswd 
		              from users where username = ?""", (username,))
		assert cr.rowcount <= 1
		row = cr.fetchone()
		cr.close()
		if row is None:
			return "", None
		userid, username, salt, kpasswd = row
		bpwd = bytes(password, "utf-8")
		hpwd = hashlib.pbkdf2_hmac("sha512", bpwd, 
									binascii.unhexlify(salt), 100000) 
		if binascii.unhexlify(kpasswd) == hpwd:
			return self._make_session_key(userid, extra_data), userid
		else:
			return "", None
			
	def _make_session_key(self, userid, extra_data):
		now = time.time()
		timeout = self.ttl + now
		sessid = hashlib.md5(bytes(str(userid)+str(now), "utf-8")).digest()
		xsessid = binascii.hexlify(sessid)
		cr = self.connector.cursor()
		cr.execute("insert into sessions values (?, ?, ?, ?)",
				(userid, xsessid, timeout, pickle.dumps(extra_data)))
		self.connector.commit()
		cr.close()
		return xsessid
		
	def delete_user(self, username=None, userid=None):
		'''Delete a user given either its username or userid.
		
		Either username or userid must be specified.
		
		@param	username	The username (string)
		@param	userid		The userid (integer)
		
		@return OK if deleted, NOT_FOUND if not found.
		
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
			rc = NOT_FOUND
		else:
			rc = OK
		cr.close()
		return rc
		
	def change_password(self, userid, newpassword, oldpassword=None):
		'''Change a user's password
		@param	userid		The user id, as returned by create_user()
		@param	newpassword	The new password
		@param	oldpassword	The current password
		
		If specified, oldpassword is checked against the current password
		and the call will fail if they don't match.
		If oldpassword is not specified, the password will be changed unconditionally.
		
		@returns OK, NOT_FOUND or REJECTED
		'''		
		cr = self.connector.cursor()
		cr.execute("select username from users where userid = ?",
					(userid,))
		row = cr.fetchone()
		if row is None:
			cr.close()
			return NOT_FOUND
		username = row[0]

		if oldpassword is not None:
			key, uid = self.validate_user(username, oldpassword)
			if not key:
				return REJECTED
			self._kill_session(key)

		bpwd = bytes(newpassword, "utf-8")
		salt = os.urandom(16)
		hashpwd = hashlib.pbkdf2_hmac("sha512", bpwd, salt, 100000)
		cr.execute("update users set kpasswd = ?, salt = ? where userid = ?",
					(binascii.hexlify(hashpwd), 
					 binascii.hexlify(salt),
					 userid))
		self.connector.commit()
		cr.close()
		return OK
		
	def _kill_session(self, key):
		cr = self.connector.cursor()
		cr.execute("delete from sessions where key = ?", (key,))
		self.connector.commit()
		cr.close()
		
	def check_key(self, key):
		'''Reset the session timeout.
		@param	key	The session key returned by validate_user()
		@returns	Tuple of the form (rc, username, userid, extra_data)
					where rc is OK, NOT_FOUND or EXPIRED
					if NOT_FOUND or EXPIRED, username and userid will be None
					
		Resets the key's Time To Live to TIMEOUT
		'''
		cr = self.connector.cursor()
		cr.execute("""select t1.userid, t1.key, t1.expiration,
		                     t1.extra_data, t2.username
		    from sessions as t1, users as t2
		    where  t1.userid = t2.userid and
		           t1.key = ?""", (key,))
		session_row = cr.fetchone()
		if session_row is None:
			cr.close()
			return (NOT_FOUND, None, None, None)
		now = time.time()
		uid, key, timeout, extra, username = session_row
		extra_data = pickle.loads(extra)
		if timeout < now:
			cr.execute("delete from sessions where key = ?", (key,))
			self.connector.commit()
			cr.close()
			return (EXPIRED, None, None, None)
		
		timeout = now + self.ttl
		cr.execute("""update sessions set expiration = ? 
		              where key = ?""", (timeout, key))
		self.connector.commit()
		cr.close()
		return (OK, username, uid, extra_data)
		
	def set_session_TTL(self, secs):
		'''Sets the TTL for all sessions.
		@param	secs	number of seconds of Time To Live.
		All new sessions or checked sessions will be set to this new TTL value.
		'''
		self.ttl = secs
		
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
		
	def modify_user(self, userid, username=None, email=None, extra_data=None):
		'''Modify user data.
		@param userid	The user id as returned by create_user()
		@param username	The new username to change, if specified.
		@param email	The new email to change, if specified.
		@param extra_data The new extra_data to change, if specified.
		
		@returns OK if successful NOT_FOUND if not.
		'''
		rc = OK
		fields_sql = []
		fields_list = []
		if username is not None:
			fields_sql.append("username = ?")
			fields_list.append(username)
		if email is not None:
			fields_sql.append("email = ?")
			fields_list.append(email)
		if extra_data is not None:
			fields_sql.append("extra_data = ?")
			fields_list.append(pickle.dumps(extra_data))
			
		if fields_list:
			query = ("update users set " 
					+ ", ".join(fields_sql) 
					+ " where userid = ?")

			fields_list.append(userid)
			
			cr = self.connector.cursor()
			cr.execute(query, fields_list)
			if cr.rowcount <= 0:
				rc = NOT_FOUND
			self.connector.commit()
			cr.close()
			
		return rc
			
		

def dbm_select(connector_name):
	Database.install_connector(connector_name)
	
		
def _dbinit(db):
	'''Create a new database structure
	'''		
	sql = [  # statements to be executed in sequence
	'''create table if not exists users (
			userid		integer primary key autoincrement,
			username	varchar(20) unique,
			email		varchar(128) unique,
			salt		varchar(32),
			kpasswd		varchar(128),
			extra_data	blob
			)
	''',
	'''create table if not exists sessions (
			userid	integer,
			key 	varchar(32),
			expiration real,
			extra_data	blob
			)
	''',
	      ]

	for stmt in sql:
		db.execute(stmt)
	db.commit()
	return db
