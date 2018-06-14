"""Test item models."""
from bodega_core.models import Item
from django.db import models


class BasicItem(Item):
    CHOICE_A = 'A'
    CHOICE_B = 'B'
    CHOICE_C = 'C'
    CHOICE_D = 'D'
    CHOICE_CHOICES = (
        (CHOICE_A, CHOICE_A),
        (CHOICE_B, CHOICE_B),
        (CHOICE_C, CHOICE_C),
        (CHOICE_D, CHOICE_D))

    boolean = models.BooleanField(default=False)

    string = models.CharField(max_length=255, null=False, blank=True)

    choice = models.CharField(max_length=4, null=False, blank=False,
                              choices=CHOICE_CHOICES)


class ComplexItem(Item):
    number = models.IntegerField(null=False, blank=False)
