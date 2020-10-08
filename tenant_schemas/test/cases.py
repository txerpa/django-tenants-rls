from django.conf import settings
from django.db import connection
from django.test import TestCase
from tenant_schemas.utils import get_tenant_model

ALLOWED_TEST_DOMAIN = '.test.com'


class TenantTestCase(TestCase):
    @classmethod
    def add_allowed_test_domain(cls):
        # ALLOWED_HOSTS is a special setting of Django setup_test_environment so we can't modify it with helpers
        if ALLOWED_TEST_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [ALLOWED_TEST_DOMAIN]

    @classmethod
    def remove_allowed_test_domain(cls):
        if ALLOWED_TEST_DOMAIN in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(ALLOWED_TEST_DOMAIN)

    @classmethod
    def setUpClass(cls):
        cls.add_allowed_test_domain()
        tenant_domain = 'tenant.test.com'
        tenant_model_class = get_tenant_model()
        cls.tenant = tenant_model_class(domain_url=tenant_domain, schema_name='test')
        cls.tenant.save()
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        pass

    @classmethod
    def sync_shared(cls):
        pass


class FastTenantTestCase(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        cls.add_allowed_test_domain()
        tenant_domain = 'tenant.test.com'
        TenantModel = get_tenant_model()
        try:
            cls.tenant = TenantModel.objects.get(domain_url=tenant_domain, schema_name='test')
        except:
            cls.tenant = TenantModel(domain_url=tenant_domain, schema_name='test')
            cls.tenant.save()

        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.remove_allowed_test_domain()
