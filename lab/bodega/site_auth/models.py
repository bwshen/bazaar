from django.conf import settings
from django.db import models
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

# Create your models here.

# Signal receivers placed alongside models as recommended by the Django REST
# Framework documentation.


# A post_save receiver as described at
# http://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
@receiver(models.signals.post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
