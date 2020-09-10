from django.conf import settings
from django.db import connection, models

from tenant_schemas.fields import RLSForeignKey
from tenant_schemas.signals import post_schema_sync
from tenant_schemas.utils import get_tenant_model, get_tenant_field


class TenantQueryset(models.QuerySet):
    """
    QuerySet for instances that inherit from the TenantMixin.
    """

    def delete(self):
        """
        Make sure we call the delete method of each object in the queryset so
        that safety checks and schema deletion (if requested) are executed
        even when using bulk delete.
        """
        counter, counter_dict = 0, {}
        for obj in self:
            result = obj.delete()
            if result is not None:
                current_counter, current_counter_dict = result
                counter += current_counter
                counter_dict.update(current_counter_dict)
        if counter:
            return counter, counter_dict


class TenantMixin(models.Model):
    """
    All tenant models must inherit this class.
    """

    domain_url = models.CharField(max_length=128, unique=True)
    schema_name = models.CharField(max_length=63, unique=True)
    objects = TenantQueryset.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.pk is None:
            post_schema_sync.send(sender=TenantMixin, tenant=self)


def get_tenant():
    tenant = connection.tenant
    if tenant is None:
        raise Exception("No tenant configured in db connection, connection.tenant is none")
    model = get_tenant_model()
    return tenant if isinstance(tenant, model) else model(schema_name=tenant.schema_name)


class MultitenantMixin(models.Model):
    """
    Mixin for any shared schema table (multitenant table). Adds a FK to the Tenant Model
    and enforces all constraints to the table to work with Row Level Security.
    """

    tenant = RLSForeignKey(
        settings.TENANT_MODEL,
        to_field=get_tenant_field(),
        blank=True,
        default=get_tenant,
        on_delete=models.PROTECT
    )

    class Meta:
        abstract = True
