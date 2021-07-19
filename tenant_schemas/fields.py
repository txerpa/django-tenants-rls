from django.db import models
from django.conf import settings

from .utils import get_tenant_field


class RLSForeignKey(models.ForeignKey):
    rls_required = True


def generate_rls_fk_field():
    """
    This method generate the rls foreign key relation field and it aims to unify this definition in a single point
    """
    from .models import get_tenant
    return RLSForeignKey(
        settings.TENANT_MODEL,
        to_field=get_tenant_field(),
        blank=True,
        default=get_tenant,
        on_delete=models.PROTECT
    )
