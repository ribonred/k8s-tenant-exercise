# myapp/k8s.py
from kubernetes import client, config
import logging
from pydantic import BaseModel, Field
import json

class Tenant(BaseModel):
    tenantName: str
    domain: str
    dbVolumeSize: str
    namespace: str = Field(alias="tenantNamespace")
    config: dict | None = Field(alias="ConfigMapReference", default=None)

    def get_config_ref(self) -> dict:
        if self.config is None:
            return {}
        return {"ConfigMapReference": self.config}


class TenantDbDetail(BaseModel):
    username: str = "default_tenant_user"
    password: str = "default_tenant_password"
    database: str = "default_tenant"
    storage: str = "1Gi"


class TenantPostgresAuth(TenantDbDetail):
    enablePostgresUser: bool = True
    postgresPassword: str = "postgres"

    @classmethod
    def from_tenant_db(cls, tenant_db: TenantDbDetail):
        return cls(
            username=tenant_db.username,
            password=tenant_db.password,
            database=tenant_db.database,
            storage=tenant_db.storage,
        )


class TenantDbPersistence(BaseModel):
    enabled: bool = True
    existingClaim: str = "pg-storage"
    size: str

    def model_dump(self, *args, **kwargs):
        dumped: dict = super().model_dump(*args, **kwargs)
        return dict(persistence=dumped)


class TenantDbSetup(BaseModel):
    db: TenantDbDetail
    auth: TenantPostgresAuth
    primary: TenantDbPersistence


logger = logging.getLogger(__name__)


def create_helmrelease_cr(tenant: Tenant):
    """
    Create a HelmRelease custom resource for the given tenant.
    This CR will instruct the Helm Operator to deploy the tenant stack.
    """
    # Load Kubernetes configuration.
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

    # Create a custom objects API client.
    custom_api = client.CustomObjectsApi()
    k8s_client = client.CoreV1Api()
    print("Creating namespace for tenant")
    k8s_client.create_namespace(
        body=client.V1Namespace(metadata=client.V1ObjectMeta(name=tenant.namespace))
    )
    k8s_client.create_namespaced_persistent_volume_claim(
        namespace=tenant.namespace,
        body=client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name="pg-storage"),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": tenant.dbVolumeSize}
                ),
            ),
        ),
    )
    print(f"Namespace {tenant.namespace} created")

    # These values should match your Helm Operator's CRD.
    group = "helm.toolkit.fluxcd.io"  # adjust if your operator uses a different group
    version = "v2"
    # Build the HelmRelease custom resource.
    tenant_db_detail = TenantDbDetail()
    tenant_db = TenantDbSetup(
        db=tenant_db_detail,
        auth=TenantPostgresAuth.from_tenant_db(tenant_db_detail),
        primary=TenantDbPersistence(size=tenant.dbVolumeSize),
    )
    helmrelease_cr = {
        "apiVersion": f"{group}/{version}",
        "kind": "HelmRelease",
        "metadata": {
            "name": f"{tenant.tenantName}-release",  # ensure this is unique
            "namespace": tenant.namespace,  # or use a dedicated namespace per tenant if desired
        },
        "spec": {
            "releaseName": f"{tenant.tenantName}",
            "interval": "10m",
            "timeout": "5m",
            "chart": {
                "spec": {
                    "chart": "tenant-stack",  # Name of your Helm chart
                    "version": "0.1.6",
                    "sourceRef": {
                        "kind": "HelmRepository",  # This must match your repository CRD kind
                        "name": "tenant-charts",  # Name of the HelmRepository containing your chart
                        "namespace": "flux-system",  # Namespace where the HelmRepository exists
                    },
                }
            },
            "values": {
                **tenant_db.model_dump(),
                "backendApp": {
                    "image": "car-finance:latest",
                    "replicaCount": 1,
                    "port": 8000,
                },
                "tenantIngress": {
                    "domain": tenant.domain  # used by the chart's ingress template
                },
            },
        },
    }
    if tenant.get_config_ref():
        helmrelease_cr["spec"]["values"]["backendApp"].update(tenant.get_config_ref())
    print(json.dumps(helmrelease_cr, indent=2))

    try:
        custom_api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=tenant.namespace,
            plural="helmreleases",
            body=helmrelease_cr,
        )
        logger.info("HelmRelease CR created for tenant '%s'", tenant.domain)
    except client.rest.ApiException as e:
        logger.error(
            "Error creating HelmRelease CR for tenant '%s': %s", tenant.domain, e
        )
        k8s_client.delete_namespace(name=tenant.namespace)

def delete_tenant_ns(tenant: Tenant):
    """
    Delete the namespace for the given tenant.
    """
    # Load Kubernetes configuration.
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

    # Create a custom objects API client.
    k8s_client = client.CoreV1Api()
    try:
        k8s_client.delete_namespace(name=tenant.namespace)
        logger.info("Namespace '%s' deleted", tenant.namespace)
    except client.rest.ApiException as e:
        logger.error("Error deleting namespace '%s': %s", tenant.namespace, e)

# tenant = Tenant(
#     tenantName="mytenant",
#     domain="mytenant.localhost",
#     dbVolumeSize="1Gi",
#     namespace="mytenant",
# )
# create_helmrelease_cr(tenant)
