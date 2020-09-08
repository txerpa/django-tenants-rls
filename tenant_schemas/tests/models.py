from tenant_schemas.models import TenantMixin
from django.db import models


class Tenant(TenantMixin, models.Model):
    pass

    class Meta:
        app_label = 'tenant_schemas'
