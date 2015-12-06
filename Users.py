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
	
	def create_user(self, username, password, email, extra_data=None):
		'''Create a user in the UserSpace's database.
		@param username	The username to be created
		@param password The user's password in cleartext
		@param email	Email for notifications or password recovery.
		@param extra_data An application dependent dictionary to be stored
						as a pickle (e.g. phone number, password reminders,
						etc)
						
		@return Integer representing the user id
		'''
		pass
		
	def validate_user(self, username, password):
		'''Validates (or logs in) a username.
		@param	username	The user's username
		@param 	password	The user's password in cleartext
		
		@return	Session key, as a string or empty string if not found 
				or wrong password.
		'''
		pass	
		
	def delete_user(self, username=None, userid=None):
		'''Delete a user given either its username or userid.
		
		Either username or userid must be specified.
		
		@param	username	The username (string)
		@param	userid		The userid (integer)
		
		@return OK if deleted, NO_SUCH_USER if not found.
		
		@throws BadCallError if neither username or userid are specified.
		'''
		pass
		
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
		'''
		pass
		

def dbm_select(connector_name):
	Database.install_connector(connector_name)
	
		
def __dbinit(database):
	'''Create a new database structure
	'''		
	sql = [  # statements to be executed in sequence
	'''create table users (
			userid		integer primary key autoincrement,
			username	varchar(20),
			email		varchar(128),
			salt		varchar(16),
			kpasswd		varchar(32),
			extra_data	blob
			)
	''',
	'''create table sessions (
			userid	integer,
			key 	varchar(64),
			expiration integer
			)
	''',
	      ]
