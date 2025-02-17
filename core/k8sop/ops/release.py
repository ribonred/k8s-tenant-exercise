# myapp/k8s.py
import logging
from pydantic import BaseModel, Field, AliasChoices
import json
from shared.k8sclient import Client
from kubernetes import client as kube

logger = logging.getLogger(__name__)
client: Client = Client()


class Tenant(BaseModel):
    tenantName: str
    dbVolumeSize: str = Field(
        validation_alias=AliasChoices("db_volume_size", "dbVolumeSize")
    )
    namespace: str = Field(
        validation_alias=AliasChoices("tenantNamespace", "tenant_namespace")
    )
    config: dict | None = Field(
        validation_alias=AliasChoices("configMapReference", "config_map_reference"),
        default=None,
    )
    domain: str
    backendImage: str

    def get_config_ref(self) -> dict:
        if self.config is None:
            return {}
        return {"configMapReference": self.config}


class TenantDbDetail(BaseModel):
    username: str = "banjar_tenant"
    password: str = "banjar_tenant_password"
    database: str = "default_tenant"


class TenantPostgresAuth(TenantDbDetail):
    enablePostgresUser: bool = True
    postgresPassword: str = "postgres"

    @classmethod
    def from_tenant_db(cls, tenant_db: TenantDbDetail):
        return cls(
            username=tenant_db.username,
            password=tenant_db.password,
            database=tenant_db.database,
        )


class TenantDbPersistence(BaseModel):
    enabled: bool = True
    existingClaim: str = "pg-storage"
    size: str

    def model_dump(self, *args, **kwargs):
        dumped: dict = super().model_dump(*args, **kwargs)
        return dict(persistence=dumped)


class PostgresConfig(BaseModel):
    architecture: str = "standalone"
    auth: TenantPostgresAuth
    primary: TenantDbPersistence


class TenantDbSetup(BaseModel):
    db: TenantDbDetail
    postgresql: PostgresConfig


def create_tenant(tenant: Tenant):
    """
    Create a HelmRelease custom resource for the given tenant.
    This CR will instruct the Helm Operator to deploy the tenant stack.
    """

    logger.info("Creating namespace for tenant")
    client.k8s.create_namespace(
        body=kube.V1Namespace(metadata=kube.V1ObjectMeta(name=tenant.namespace))
    )
    client.k8s.create_namespaced_persistent_volume_claim(
        namespace=tenant.namespace,
        body=kube.V1PersistentVolumeClaim(
            metadata=kube.V1ObjectMeta(name="pg-storage"),
            spec=kube.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=kube.V1ResourceRequirements(
                    requests={"storage": tenant.dbVolumeSize}
                ),
            ),
        ),
    )
    logger.info(f"Namespace {tenant.namespace} created")

    # These values should match your Helm Operator's CRD.
    group = "helm.toolkit.fluxcd.io"  # adjust if your operator uses a different group
    version = "v2"
    # Build the HelmRelease custom resource.
    tenant_db_detail = TenantDbDetail()
    tenant_db = TenantDbSetup(
        db=tenant_db_detail,
        postgresql=PostgresConfig(
            auth=TenantPostgresAuth.from_tenant_db(tenant_db_detail),
            primary=TenantDbPersistence(size=tenant.dbVolumeSize),
        ),
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
            "interval": "1m",
            "timeout": "5m",
            "chart": {
                "spec": {
                    "chart": "tenant-stack",  # Name of your Helm chart
                    "version": "1.0.1",
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
                    "image": tenant.backendImage,
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
    logger.info(json.dumps(helmrelease_cr, indent=2))

    try:
        client.crd.create_namespaced_custom_object(
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
        client.k8s.delete_namespace(name=tenant.namespace)


def delete_tenant_ns(tenant: Tenant):
    """
    Delete the namespace for the given tenant.
    """
    try:
        client.k8s.delete_namespace(name=tenant.namespace)
        logger.info("Namespace '%s' deleted", tenant.namespace)
    except kube.rest.ApiException as e:
        logger.error("Error deleting namespace '%s': %s", tenant.namespace, e)


def update_tenant_release(tenant: Tenant):
    # These values should match your Helm Operator's CRD.
    group = "helm.toolkit.fluxcd.io"  # adjust if your operator uses a different group
    version = "v2"
    # Build the HelmRelease custom resource.
    tenant_db_detail = TenantDbDetail()
    tenant_db = TenantDbSetup(
        db=tenant_db_detail,
        postgresql=PostgresConfig(
            auth=TenantPostgresAuth.from_tenant_db(tenant_db_detail),
            primary=TenantDbPersistence(size=tenant.dbVolumeSize),
        ),
    )
    release_name = f"{tenant.tenantName}-release"

    values = {
        **tenant_db.model_dump(),
        "backendApp": {
            "image": tenant.backendImage,
            "replicaCount": 1,
            "port": 8000,
        },
        "tenantIngress": {
            "domain": tenant.domain  # used by the chart's ingress template
        },
    }
    if tenant.get_config_ref():
        values["backendApp"].update(tenant.get_config_ref())
    try:
        # Fetch the existing HelmRelease
        existing_helmrelease = client.crd.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=tenant.namespace,
            plural="helmreleases",
            name=release_name,
        )

        # Keep metadata, but update `spec`
        existing_helmrelease["spec"]["values"] = values

        # Update the HelmRelease with the new values
        updated_helmrelease = client.crd.replace_namespaced_custom_object(
            group=group,
            version=version,
            namespace=tenant.namespace,
            plural="helmreleases",
            name=release_name,
            body=existing_helmrelease,
        )

        logger.info(f"HelmRelease CR updated for tenant {tenant.domain}")
        return updated_helmrelease

    except client.rest.ApiException as e:
        logger.error(f"Error updating HelmRelease CR for tenant {tenant.domain}: {e}")
