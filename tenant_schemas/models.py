from django.conf import settings
from django.core import checks
from django.db import connection, models

from .fields import RLSForeignKey
from .signals import post_schema_sync
from .utils import get_tenant_model, get_tenant_field


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


def generate_rls_fk_field():
    """
    This method generate the rls foreign key relation field and it aims to unify this definition in a single point
    """
    return RLSForeignKey(
        settings.TENANT_MODEL,
        to_field=get_tenant_field(),
        blank=True,
        default=get_tenant,
        on_delete=models.PROTECT
    )


class MultitenantMixin(models.Model):
    """
    Mixin for any shared schema table (multitenant table). Adds a FK to the Tenant Model
    and enforces all constraints to the table to work with Row Level Security.
    """

    tenant = generate_rls_fk_field()

    class Meta:
        abstract = True

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._run_check_tenant_field())
        errors.extend(cls._run_check_m2m_fields())
        errors.extend(cls._run_check_unique_together())
        return errors

    @classmethod
    def _get_tenant_field(cls):
        all_fields = cls._meta.get_fields()
        tenant_fields = [field for field in all_fields if field.name == 'tenant']
        tenant_field = tenant_fields[0] if tenant_fields else None
        return tenant_field

    @classmethod
    def _run_check_tenant_field(cls):
        tenant_field = cls._get_tenant_field()
        object_name = cls._meta.object_name

        # Ensure that tenant field are still present.
        if not tenant_field:
            return [
                checks.Critical(
                    f"tenant field not present in {object_name}",
                    obj=cls,
                    id=f'tenant_schemas.{object_name}.tenant_field.C001'
                )
            ]
        # Ensure that tenant field is instance of RLSForeignKey.
        elif not isinstance(tenant_field, RLSForeignKey):
            return [
                checks.WARNING(
                    f"tenant field isn't instance of {RLSForeignKey.__name__} in {object_name}",
                    obj=cls,
                    id=f'tenant_schemas.{object_name}.tenant_field.W001'
                )
            ]

        return list()

    @classmethod
    def _run_check_m2m_fields(cls):
        all_fields = cls._meta.get_fields()

        warnings = list()

        # Ensure that m2m field related model has tenant field and is an instance of RLSForeignKey
        m2m_fields = (field for field in all_fields if isinstance(field, models.ManyToManyField))
        for m2m_field in m2m_fields:
            through_all_fields = m2m_field.remote_field.through._meta.get_fields()
            through_tenant_fields = [field for field in through_all_fields if field.name == 'tenant']
            through_tenant_field = through_tenant_fields[0] if through_tenant_fields else None
            through_object_name = m2m_field.remote_field.through._meta.object_name

            auto_or_manual_model = 'auto-created' if m2m_field.remote_field.through._meta.auto_created else 'manual'

            if not through_tenant_field:
                warnings.append(
                    checks.Warning(
                        f"tenant field not present in Many2Many {auto_or_manual_model} model: {through_object_name}",
                        hint=f"Use custom defined model for through property in Many2Many field "
                             f"{cls._meta.object_name}.{m2m_field.name} using {MultitenantMixin.__name__} "
                             f"in the model definition",
                        id=f'tenant_schemas.{through_object_name}.m2m_field.W001'
                    )
                )
            elif not isinstance(through_tenant_field, RLSForeignKey):
                warnings.append(
                    checks.Warning(
                        f"tenant field isn't instance of RLSForeignKey in {through_object_name}",
                        id=f'tenant_schemas.{through_object_name}.m2m_field.W002'

                    )
                )

        return warnings

    @classmethod
    def _run_check_unique_together(cls):
        warnings = list()

        if cls._meta.unique_together:
            object_name = cls._meta.object_name
            tenant_field = cls._get_tenant_field()
            for unique_together in cls._meta.unique_together:
                if tenant_field.name not in unique_together:
                    warnings.append(
                        checks.Warning(
                            f"tenant field isn't in unique_together in {object_name}: {unique_together}",
                            id=f'tenant_schemas.{object_name}.unique_together_without_tenant.W001'

                        )
                    )

        return warnings
