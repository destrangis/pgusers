import importlib

DEFAULT_CONNECTOR = "sqlite3"

class Database(object):
	connector = None
	
	@classmethod
	def install_connector(cls, name):
		if not name:
			name = DEFAULT_CONNECTOR
		cls.connector = importlib.import_module(name)
		 
	def __getattr__(self, attrname):
		if self.connector is None:
			self.install_connector(DEFAULT_CONNECTOR)
		return self.connector.__dict__[attrname]
