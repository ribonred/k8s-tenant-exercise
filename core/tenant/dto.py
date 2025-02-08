from pydantic import BaseModel
from .models import Tenant

class TenantMeta(BaseModel):
    name: str
    namespace: str = "tenant-system"

class TenantSpec(BaseModel):
    tenantName: str
    domain: str
    dbVolumeSize: str
    tenantNamespace: str
    configMapReference: dict

class TenantCrd(BaseModel):
    apiVersion: str = "saas.com/v1"
    kind: str = "Tenant"
    metadata: TenantMeta
    spec: TenantSpec

    @classmethod
    def create_from_model(cls, tenant: Tenant):
        return cls(
            metadata=TenantMeta(name=tenant.name),
            spec=TenantSpec(
                tenantName=tenant.name,
                domain=tenant.domain,
                dbVolumeSize=tenant.db_volume_size,
                tenantNamespace=tenant.tenant_namespace,
                configMapReference=tenant.config_map_reference
            ),
        )
