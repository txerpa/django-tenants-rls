from rest_framework import serializers

from tenant_schemas.models import MultitenantMixin, get_tenant
from .utils import is_bad_tenant_field_config


class RLSModelSerializer(serializers.ModelSerializer):
    """
    This class add 'tenant' as HiddenField when '__all__' is specified as Meta.fields value or when 'tenant' is not
    included in Meta.exclude.
    Hidden fields are omitted on reads, but are considered on writes in order to check unique validators.

    This is because if this field has other type, a select is made for each object of the result, to obtain the value
    of the client model. If tenant field is omitted on write, unique_validators are not executed, and in the case of
    duplicated values a 5xx error is given instead of 400 error.
    """

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(instance, *args, **kwargs)

        model = getattr(self.Meta, 'model', None)
        if issubclass(model, MultitenantMixin):
            if is_bad_tenant_field_config(self):
                self.fields['tenant'] = serializers.HiddenField(default=get_tenant)


