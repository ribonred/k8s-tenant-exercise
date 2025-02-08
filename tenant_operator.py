import kopf
from main import create_helmrelease_cr, Tenant, delete_tenant_ns
@kopf.on.create('tenants')
def create_fn(spec, name, meta, status, **kwargs):
    print(f'Resource {name} was created')
    tenant = Tenant.model_validate(spec)
    print(f'Spec: {tenant}')
    create_helmrelease_cr(tenant)

@kopf.on.delete('tenants')
def delete_tenant(spec, name, meta, status,namespace, **kwargs):
    print(f'spec {spec} was deleted')
    tenant = Tenant.model_validate(spec)
    delete_tenant_ns(tenant)
    print(f'Resource {name} was deleted in ns {namespace} and tenant {tenant}')
    