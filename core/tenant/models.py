from django.db import models

# Create your models here.
class Tenant(models.Model):
    name = models.CharField(max_length=255)
    subdomain_prefix = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name