from django.contrib import admin
from .models import Tenant
from .dto import TenantCrd
from kubernetes import client, config
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
import logging

logger = logging.getLogger(__name__)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {"widget": JSONEditorWidget},
    }
    list_display = (
        "name",
        "resource_status",
        "subdomain_prefix",
        "db_volume_size",
        "tenant_namespace",
        "config_map_reference",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "subdomain_prefix", "tenant_namespace")
    list_filter = ("created_at", "updated_at")
    actions = ["create_resource", "delete_resource", "update_resource"]

    def get_k8s_config(self):
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        return client.CustomObjectsApi()

    def create_k8s_resource(self, obj: Tenant):
        crd_api = self.get_k8s_config()
        tenant_crd: TenantCrd = TenantCrd.create_from_model(obj)
        try:
            response = crd_api.create_namespaced_custom_object(
                group="saas.com",
                version="v1",
                namespace=tenant_crd.metadata.namespace,
                plural="tenants",  # Must match the `plural` defined in CRD
                body=tenant_crd.model_dump(),
            )
            logger.info("Tenant CR created for tenant '%s'", obj.name)
            logger.debug(response)
            obj.resource_status = Tenant.ResourceStatus.READY
        except client.rest.ApiException as e:
            logger.error("Error creating Tenant CR for tenant '%s': %s", obj.name, e)

    def create_resource(self, request, queryset):
        for obj in queryset:
            self.create_k8s_resource(obj)
            obj.save()

    def delete_resource(self, request, queryset):
        crd_api = self.get_k8s_config()

        for obj in queryset:
            try:
                tenant_crd: TenantCrd = TenantCrd.create_from_model(obj)
                crd_api.delete_namespaced_custom_object(
                    group="saas.com",
                    version="v1",
                    namespace=tenant_crd.metadata.namespace,
                    plural="tenants",
                    name=obj.name,
                )
                logger.info("Tenant CR deleted for tenant '%s'", obj.name)
                obj.resource_status = Tenant.ResourceStatus.NOT_CREATED
            except client.rest.ApiException as e:
                logger.error(
                    "Error deleting Tenant CR for tenant '%s': %s", obj.name, e
                )
            obj.save()

    def update_resource(self, request, queryset):
        crd_api = self.get_k8s_config()

        for obj in queryset:
            try:
                tenant_crd: TenantCrd = TenantCrd.create_from_model(obj)
                existing_tenant_config = crd_api.get_namespaced_custom_object(
                    group="saas.com",
                    version="v1",
                    namespace=tenant_crd.metadata.namespace,
                    plural="tenants",
                    name=tenant_crd.metadata.name,
                )
                existing_tenant_config["spec"] = tenant_crd.spec.model_dump()
                print(tenant_crd)
                crd_api.patch_namespaced_custom_object(
                    group="saas.com",
                    version="v1",
                    namespace=tenant_crd.metadata.namespace,
                    plural="tenants",
                    name=obj.name,
                    body=existing_tenant_config,
                )
                logger.info("Tenant CR updated for tenant '%s'", obj.name)
            except client.rest.ApiException as e:
                print(e)
                logger.error(
                    "Error updating Tenant CR for tenant '%s': %s", obj.name, e
                )
