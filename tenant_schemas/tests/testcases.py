import inspect

from django.conf import settings
from django.db import connection
from django.test import TestCase

from tenant_schemas.utils import get_public_schema_name


class BaseTestCase(TestCase):
    """
    Base test case that comes packed with overloaded INSTALLED_APPS,
    custom public tenant, and schemas cleanup on tearDown.
    """
    @classmethod
    def setUpClass(cls):
        settings.TENANT_MODEL = 'tenant_schemas.Tenant'
        super(BaseTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(BaseTestCase, cls).tearDownClass()
        if '.test.com' in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove('.test.com')

    def setUp(self):
        connection.set_schema_to_public()
        super(BaseTestCase, self).setUp()

    @classmethod
    def get_verbosity(self):
        for s in reversed(inspect.stack()):
            options = s[0].f_locals.get('options')
            if isinstance(options, dict):
                return int(options['verbosity']) - 2
        return 1
