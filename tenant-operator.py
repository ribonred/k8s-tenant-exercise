import kopf
from core.k8sop.ops import release
import logging

logger = logging.getLogger(__name__)


@kopf.on.create("tenants")
def create_tenant(spec, name, meta, status, **kwargs):
    logger.info(f"Resource {name} was created")
    tenant = release.Tenant.model_validate(spec)
    logger.info(f"Spec: {tenant}")
    release.create_tenant(tenant)


@kopf.on.delete("tenants")
def delete_tenant(spec, name, meta, status, namespace, **kwargs):
    logger.info(f"spec {spec} was deleted")
    tenant = release.Tenant.model_validate(spec)
    release.delete_tenant_ns(tenant)
    logger.info(f"Resource {name} was deleted in ns {namespace} and tenant {tenant}")


@kopf.on.update("tenants")
def update_tenant(spec, name, meta, status, **kwargs):
    logger.info(f"Resource {name} was updated")
    tenant = release.Tenant.model_validate(spec)
    logger.info(f"Spec: {tenant}")
    release.update_tenant_release(tenant)
