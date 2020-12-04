
def is_bad_tenant_field_config(serializer_class):
    fields = getattr(serializer_class.Meta, 'fields', None)
    exclude = getattr(serializer_class.Meta, 'exclude', None)
    bad_tenant_field_config = (
        fields == '__all__' or
        (
            fields is None and
            isinstance(exclude, (list, tuple)) and
            'tenant' not in exclude
        )
    )
    return bad_tenant_field_config
