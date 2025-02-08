from django.db import models

# Create your models here.
class Tenant(models.Model):
    class ResourceStatus(models.TextChoices):
        NOT_CREATED = 'not_created'
        READY = 'ready'
    name = models.CharField(max_length=255)
    subdomain_prefix = models.CharField(max_length=255, unique=True)
    db_volume_size = models.CharField(max_length=10)
    tenant_namespace = models.CharField(max_length=50, unique=True)
    config_map_reference = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resource_status = models.CharField(max_length=20, choices=ResourceStatus.choices, default=ResourceStatus.NOT_CREATED)

    def __str__(self):
        return self.name
    
    @property
    def domain(self):
        return f"{self.subdomain_prefix}.localhost"