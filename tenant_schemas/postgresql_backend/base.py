import psycopg2

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError
import django.db.utils

from tenant_schemas.postgresql_backend.schema import RLSDatabaseSchemaEditor
from tenant_schemas.utils import get_public_schema_name, get_limit_set_calls


ORIGINAL_BACKEND = getattr(
    settings, "ORIGINAL_BACKEND", "django.db.backends.postgresql_psycopg2"
)
# Django 1.9+ takes care to rename the default backend to 'django.db.backends.postgresql'
original_backend = django.db.utils.load_backend(ORIGINAL_BACKEND)


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to manipulate the search_path using set_tenant and set_schema_name
    """

    include_public_schema = True
    SchemaEditorClass = RLSDatabaseSchemaEditor

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.set_schema_to_public()

    def close(self):
        self.search_path_set = False
        super(DatabaseWrapper, self).close()

    def rollback(self):
        super(DatabaseWrapper, self).rollback()
        # Django's rollback clears the search path so we have to set it again the next time.
        self.search_path_set = False

    def set_tenant(self, tenant, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.set_schema(tenant.schema_name, include_public)
        self.tenant = tenant

    def set_schema(self, schema_name, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = FakeTenant(schema_name=schema_name)
        self.schema_name = schema_name
        self.include_public_schema = include_public
        self.set_settings_schema(schema_name)
        self.search_path_set = False
        # Content type can no longer be cached as public and tenant schemas
        # have different models. If someone wants to change this, the cache
        # needs to be separated between public and shared schemas. If this
        # cache isn't cleared, this can cause permission problems. For example,
        # on public, a particular model has id 14, but on the tenants it has
        # the id 15. if 14 is cached instead of 15, the permissions for the
        # wrong model will be fetched.
        ContentType.objects.clear_cache()

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.set_schema(get_public_schema_name())

    def set_settings_schema(self, schema_name):
        self.settings_dict["SCHEMA"] = schema_name

    def _cursor(self, name=None):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """
        if name:
            # Only supported and required by Django 1.11 (server-side cursor)
            cursor = super(DatabaseWrapper, self)._cursor(name=name)
        else:
            cursor = super(DatabaseWrapper, self)._cursor()

        # optionally limit the number of executions - under load, the execution
        # of `set search_path` can be quite time consuming
        if (not get_limit_set_calls()) or not self.search_path_set:
            # Actual search_path modification for the cursor. Database will
            # search schemata from left to right when looking for the object
            # (table, index, sequence, etc.).
            if not self.schema_name:
                raise ImproperlyConfigured(
                    "Database schema not set. Did you forget "
                    "to call set_schema() or set_tenant()?"
                )
            public_schema_name = get_public_schema_name()
            if self.schema_name == public_schema_name:
                # should we treat it different?
                pass

            if name:
                # Named cursor can only be used once
                cursor_for_tenant_property = self.connection.cursor()
            else:
                # Reuse
                cursor_for_tenant_property = cursor

            # In the event that an error already happened in this transaction and we are going
            # to rollback we should just ignore database error when setting the search_path
            # if the next instruction is not a rollback it will just fail also, so
            # we do not have to worry that it's not the good one
            try:
                cursor_for_tenant_property.execute(
                    f"SET txerpa.tenant = '{self.schema_name}'"
                )
            except (django.db.utils.DatabaseError, psycopg2.InternalError):
                self.search_path_set = False
            else:
                self.search_path_set = True

            if name:
                cursor_for_tenant_property.close()

        return cursor


class FakeTenant:
    """
    We can't import any db model in a backend (apparently?), so this class is used
    for wrapping schema names in a tenant-like structure.
    """

    def __init__(self, schema_name):
        self.schema_name = schema_name
