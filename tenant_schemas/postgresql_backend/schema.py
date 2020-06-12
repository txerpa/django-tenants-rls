from pprint import pprint

from django.db import models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.conf import settings

from tenant_schemas.utils import get_tenant_model


class RLSDatabaseSchemaEditor(DatabaseSchemaEditor):

    sql_enable_rls = "ALTER TABLE %(table)s enable ROW LEVEL SECURITY"
    sql_create_policy = (
        "CREATE POLICY _po_tenant_%(table)s ON %(table)s FOR ALL USING %(policy)s"
    )
    sql_alter_column_defaul_tenant = "ALTER TABLE ONLY %(table)s ALTER COLUMN tenant_id SET DEFAULT current_setting('txerpa.tenant');"

    def create_model(self, model):
        # if any field has the rls_required flag then rls constraints are created
        enable_rls = any(field.rls_required for field in model._meta.local_fields if hasattr(field, 'rls_required'))

        super().create_model(model=model)
        # enable RLS on table and create policy
        self._set_tenant_rls(enable_rls, model)

    def add_field(self, model, field):
        enable_rls = field.rls_required if hasattr(field, 'rls_required') else False
        super().add_field(model, field)
        # enable RLS on table and create policy
        self._set_tenant_rls(enable_rls, model)

    def _set_tenant_rls(self, enable_rls, model):
        if enable_rls:
            self.execute(self.sql_enable_rls % {"table": self.quote_name(model._meta.db_table)})
            self.execute(self.sql_create_policy % {
                "table": model._meta.db_table,
                "policy": "(tenant_id = current_setting('txerpa.tenant')) with check (tenant_id = current_setting('txerpa.tenant'))"
            })
            self.execute(self.sql_alter_column_defaul_tenant % {"table": self.quote_name(model._meta.db_table)})
