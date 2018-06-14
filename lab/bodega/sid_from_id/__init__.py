"""
SIDs are IDs that are
- short, for easy reading and copying (also non-electronically, if necessary)
- searchable, to maximize the signal to noise ratio when grepping logs
- somewhat secure, to avoid leaking information about the database to users

The latter two properties are similar to UUIDs, but being short makes them
more convenient. UUIDs also require changing the primary key of models and
require more space to store (though that isn't a big deal now that UUIDField
exists). The vast majority of models use auto-increment integers as their
primary keys, and we can't change that for models we don't control such as
User. So, we encode SIDs from underlying integer IDs by encrypting them.
"""
