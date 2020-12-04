from rest_framework.serializers import ModelSerializer

from tenant_schemas.models import MultitenantMixin
from .utils import is_bad_tenant_field_config


class RLSModelSerializer(ModelSerializer):
    """
    This class remove tenant field form serializer field's when '__all__' is specified as fields value.
    If you want this field(tenant) in the serializer, you must specify in "fields" definition:
       fields = ('field1', 'field2', 'tenant', ...)

    This is because if this field is not excluded, a select is made for each object of the result, to obtain
    the value of the client model.
    """

    def get_field_names(self, *args, **kwargs):
        fields = super().get_field_names(*args, **kwargs)

        model = getattr(self.Meta, 'model', None)
        if issubclass(model, MultitenantMixin):
            if is_bad_tenant_field_config(self) and 'tenant' in fields:
                fields.remove('tenant')

        return fields
