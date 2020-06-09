from django.db.backends.ddl_references import Statement, Table
from django.db.models.constraints import BaseConstraint

__all__ = ['RLSConstraint']


class RLSConstraint(BaseConstraint):
    template_enable_rls = f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'

    def __init__(self, *, name, condition=None):
        super().__init__(name=name)

    def constraint_sql(self, model, schema_editor):
        pass

    def create_sql(self, model, schema_editor):
        return Statement(
            'ALTER TABLE %(table)s ENABLE ROW LEVEL SECURITY',
            table=Table(model._meta.db_table, schema_editor.quote_name)
        )

    def remove_sql(self, model, schema_editor):
        return schema_editor._delete_constraint_sql(
            schema_editor.sql_delete_check,
            model,
            schema_editor.quote_name(self.name),
        )
