# myapp/k8s.py
from kubernetes import client, config
import logging

logger = logging.getLogger(__name__)

def create_helmrelease_cr(tenant):
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

    # These values should match your Helm Operator's CRD.
    group = "helm.operator-sdk"  # adjust if your operator uses a different group
    version = "v1"
    plural = "helmreleases"  # typically the plural for HelmRelease is 'helmreleases'

    # Build the HelmRelease custom resource.
    helmrelease_cr = {
        "apiVersion": f"{group}/{version}",
        "kind": "HelmRelease",
        "metadata": {
            "name": f"{tenant.subdomain}-release",  # ensure this is unique
            "namespace": "default",  # or use a dedicated namespace per tenant if desired
        },
        "spec": {
            "releaseName": f"{tenant.subdomain}",
            "chart": {
                "spec": {
                    "chart": "tenant-stack",   # Name of your Helm chart
                    "version": "0.1.1",          # Version of your chart
                    "sourceRef": {
                        "kind": "HelmRepository",  # This must match your repository CRD kind
                        "name": "tenant-charts",   # Name of the HelmRepository containing your chart
                        "namespace": "flux-system"     # Namespace where the HelmRepository exists
                    },
                }
            },
            "values": {
                "tenantName": tenant.name,
                "subdomain": tenant.subdomain,
                "postgres": {
                    "image": "postgres:13",
                    "username": "tenantuser",
                    "password": "tenantpass",
                    "database": "tenantdb"
                },
                "app": {
                    "image": "mytenantapp:latest",
                    "replicaCount": 1,
                    "port": 8000,
                },
                "ingress": {
                    "host": tenant.subdomain  # used by the chart's ingress template
                }
            }
        }
    }

    try:
        custom_api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace="default",
            plural=plural,
            body=helmrelease_cr,
        )
        logger.info("HelmRelease CR created for tenant '%s'", tenant.subdomain)
    except client.rest.ApiException as e:
        logger.error("Error creating HelmRelease CR for tenant '%s': %s", tenant.subdomain, e)
