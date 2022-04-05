=======
pgusers
=======

User authentication and session management based on PostgreSQL

Installation
------------

Just download it from PYPI using pip::

    pip install pgusers

Usage
-----

In order to use this module, you instantiate a ``UserSpace`` object:

.. code-block:: python

    import pgusers

    usp = pgusers.UserSpace("userlist", host="dbhost.domain.com",
                            port=5432, user="dbuser")

Where ``userlist`` must be the name of an existing database instance on
the PostgreSQL host. The rest of the keyword arguments are those needed to
create a connection to the database server and are passed straight to
the ``psycopg2`` module.

Repeated connections to the same userspace return the same object.

The following are the methods available to ``UserSpace`` instances.

``create_user(self, username, password, email, admin=False, extra_data=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Creates a new user. Returns a numeric userid for the user created.

:username:
  The username to be created, if there is already a record with that username, a ``BadCallError`` exception is raised.
:password:
  The user's password in cleartext.
:email:
  Email for notifications or password recovery. ``BadCallError`` is raised if the email exists in the database.
:admin:
  A boolean value indicating whether the user is an administrator.
:extra_data:
  Any data that will be attached to the record. This can be anything that can be serialised using the ``pickle``  module from the standard library.


``validate_user(self, username, password, extra_data=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validates (or logs in) a user. Returns a tuple with a string
containing a session key, a boolean value indicating whether the user is
an admin, and the numeric userid. If the user was not found, the returned
tuple would be ``("", False, None)``

:username:
  The username to be authenticated.
:password:
  The password in clear text.
:extra_data:
  Optional data that will be attached to the session. This can be anything that can be serialised using the ``pickle`` module from the standard library.


``delete_user(self, username=None, userid=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Delete a user given either its username or userid. Either username or userid
must be specified. Returns ``OK`` if deleted, ``NOT_FOUND`` if not found.

:username:
    The username.
:userid:
  The numeric userid.

``change_password(self, userid, newpassword, oldpassword=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Change a user's password. Returns either ``OK``, ``NOT_FOUND`` or ``REJECTED``
Throws BadCallError if neither username or userid are specified.

:userid:
  The numeric user id, as returned by ``create_user()``
:newpassword:
  The new password, in cleartext.
:oldpassword:
  The current password, in cleartext. If specified, oldpassword is checked against the current password and the call will fail if they don't match. If ``oldpassword`` is not specified, the password will be changed unconditionally.

``check_key(self, key)``
~~~~~~~~~~~~~~~~~~~~~~~~
Reset the session timeout. Resets the key's Time To Live to the default value.
Returns a tuple of the form *(rc, username, userid, extra_data)* where rc
can be either ``OK``, ``NOT_FOUND`` or ``EXPIRED``. If ``NOT_FOUND`` or ``EXPIRED``, username
and userid will be ``None``.

:key:
  The session key as returned by ``validate_user()``

``set_session_TTL(self, secs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sets the TTL for all sessions. All new sessions or checked sessions will
be set to this new TTL value.

:secs:
  The number of seconds of Time To Live. The default TTL for a session is currently 864000 seconds, or 10 days. This might change in future releases.


``find_user(self, username=None, email=None, userid=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Find a user given either its username, its email or its userid. At least
one of those must be supplied.

This method
does not validate the user or any session. It is used to retrieve information
about a user in the database.

Returns a dictionary with fields ``userid``, ``username``, ``email``, ``admin``,
and ``extra_data``. ``None`` if the user was not found.

:username:
  The username.
:email:
  The email.
:userid:
  The numeric userid.

``modify_user(self, userid, username=None, email=None, extra_data=None)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Modify user data. Returns ``OK`` if successful ``NOT_FOUND`` if not.

:userid:
  The user id as returned by ``create_user()``
:username:
  The new username to change, if specified.
:email:
  The new email to change, if specified.
:extra_data:
  The new extra_data to change, if specified.

``is_admin(self, userid)``
~~~~~~~~~~~~~~~~~~~~~~~~~~
Checks whether the user is admin. Returns ``True`` if it is, ``False`` if not.

:userid:
  The user id as returned by ``create_user()``

``set_admin(self, userid, admin=True)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Grant or revoke admin privileges to the user. To revoke, call with admin set to ``False``

:userid:
  The user id as returned by ``create_user()``
:admin:
  If set to ``True`` or not specified, mark the user as administrator. If set to ``False``, revokes administrator rights.

``all_users(self)``
~~~~~~~~~~~~~~~~~~~
Generator yielding (userid, username, email, admin) tuples for all users
in the userspace.

``list_sessions(self, uid, expired=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generator yielding all sessions for a user or for all users (i.e. all sessions) if uid is 0. If
expired is set to ``True``, yield only the sessions that have expired.
Yields tuples of the form ``(username, key, expiration)``

:userid:
  The user id as returned by ``create_user()``, or 0 to return all sessions.
:expired:
  Boolean indicating whether the method should only return expired sessions.

``kill_sessions(self, uid, expired=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Kill the sessions for a user or for all users (i.e. all sessions) if uid is 0. If
expired is set to ``True``, kill only the sessions that have expired. *Killing* a
session removes it from the database, efectively invalidating it.


:userid:
  The user id as returned by ``create_user()``, or 0 to kill all sessions.
:expired:
  Boolean indicating whether the method should only kill the expired sessions.

License
-------
This software is licensed under the terms of the **MIT license**.
