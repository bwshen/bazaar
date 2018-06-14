from django.contrib.auth.models import User
from django.db import models

# Create your models here.

# Models are the central concept in Django and deserve the highest attention.
# These define the data model of our app and therefore have major influence
# over everything including business logic and how REST APIs are most naturally
# structured. Additionally, any schema changes here create the need to run
# database migrations, so it's desirable to think through the models and get
# them right sooner to minimize changes and migration work.

# Read about Django models at
# https://docs.djangoproject.com/en/1.10/topics/db/models/

# After adding models or making changes, we deal with generating and running
# migrations. Read about them at
# https://docs.djangoproject.com/en/1.10/topics/migrations/


# This is a model which represents a "toy" in our pretend app. We write it and
# work with it primarily as a Python class/objects, which Django will translate
# to a database table with each row representing an instance of an object.
class Toy(models.Model):
    # The main thing we do in a model class is define the fields that it has.
    # These fields pretty much correspond to SQL data types. Read about them
    # at https://docs.djangoproject.com/en/1.10/ref/models/fields/

    # This is a simple character field for storing a toy's name which should be
    # a short string.
    name = models.CharField(max_length=40)

    # This is a field which represents the owner of a toy by a reference to a
    # User object. This corresponds to a SQL foreign key.
    # It's usually a good idea to specify a default for new fields, to make
    # the schema migration easier. In this case, we make the default be None
    # and choose to represent it with a NULL SQL value. Note that we shouldn't
    # use NULL for string types:
    # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.Field.null
    owner = models.ForeignKey(User, default=None, null=True)

    # This is a field which represents the current users playing with the toy.
    # It corresponds to a table dedicated to mapping user IDs and toy IDs,
    # a common SQL convention which Django automates for us. The related_name
    # tells Django to generate a field named "playing_with_toys" on the User
    # model for convenient traversal of the related toys directly from a User
    # instance. In fact Django already did so for the owner field above, so
    # `user.toys` will query for the toys owned by that user. We need to
    # specify the name here to avoid a conflict, and `user.playing_with_toys`
    # will query for the toys that user is playing with.
    players = models.ManyToManyField(User, related_name='playing_with_toys')


# Ball, Stick, and Doll are each models that inherit from Toy in order to
# represent a more specific type of toy. Specific types of toys have their own
# fields that are only relevant for that type, and they also have the common
# fields from generic toys. In the database, each specific type is its own
# table which carries the type-specific fields and a reference to the generic
# toy table. Objects of the specific type of toy have the same ID as the
# corresponding object, and both objects have a field for referring to the
# other object. It behaves like a one-to-one relational field because that's
# in fact what it is.


# A ball is a toy that has a radius.
class Ball(Toy):
    radius = models.FloatField()


# A stick is a toy that has a length.
class Stick(Toy):
    length = models.FloatField()


# A doll is a toy that has a sex and a race.
class Doll(Toy):
    FEMALE = 'F'
    MALE = 'M'
    SEX_CHOICES = (
        (FEMALE, 'Female'),
        (MALE, 'Male'),
    )
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)

    DWARF = 'DWARF'
    ELF = 'ELF'
    HUMAN = 'HUMAN'
    ORC = 'ORC'
    RACE_CHOICES = (
        (DWARF, 'Dwarf'),
        (ELF, 'Elf'),
        (HUMAN, 'Human'),
        (ORC, 'Orc'),
    )
    race = models.CharField(max_length=16, choices=RACE_CHOICES)
