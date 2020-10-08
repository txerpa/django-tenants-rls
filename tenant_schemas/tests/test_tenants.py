import json
from io import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection

from dts_test_app.models import DummyModel, ModelWithFkToPublicUser
from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.tests.models import Tenant
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import (get_public_schema_name, get_tenant_model,
                                  schema_context, schema_exists,
                                  tenant_context)


class TenantDataAndSettingsTest(BaseTestCase):
    """
    Tests if the tenant model settings work properly and if data can be saved
    and persisted to different tenants.
    """

    @classmethod
    def setUpClass(cls):
        super(TenantDataAndSettingsTest, cls).setUpClass()
        settings.INSTALLED_APPS = ('tenant_schemas',
                                   'dts_test_app',
                                   'django.contrib.contenttypes',
                                   'django.contrib.auth', )

        Tenant(domain_url='test.com', schema_name=get_public_schema_name()).save()

    def test_tenant_schema_is_created(self):
        """
        When saving a tenant, it's schema should be created.
        """
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        self.assertTrue(schema_exists(tenant.schema_name))

    def test_sync_tenant(self):
        """
        When editing an existing tenant, all data should be kept.
        """
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        # go to tenant's path
        connection.set_tenant(tenant)

        # add some data
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()

        # edit tenant
        connection.set_schema_to_public()
        tenant.domain_url = 'example.com'
        tenant.save()

        connection.set_tenant(tenant)

        # test if data is still there
        self.assertEqual(DummyModel.objects.count(), 2)

    def test_switching_search_path(self):
        tenant1 = Tenant(domain_url='something.test.com',
                         schema_name='tenant1')
        tenant1.save()

        connection.set_schema_to_public()
        tenant2 = Tenant(domain_url='example.com', schema_name='tenant2')
        tenant2.save()

        # go to tenant1's path
        connection.set_tenant(tenant1)

        # add some data, 2 DummyModels for tenant1
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()

        # switch temporarily to tenant2's path
        with tenant_context(tenant2):
            # add some data, 3 DummyModels for tenant2
            DummyModel(name="Man,").save()
            DummyModel(name="testing").save()
            DummyModel(name="is great!").save()

        # we should be back to tenant1's path, test what we have
        self.assertEqual(2, DummyModel.objects.count())

        # switch back to tenant2's path
        with tenant_context(tenant2):
            self.assertEqual(3, DummyModel.objects.count())

    def test_switching_tenant_without_previous_tenant(self):
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        connection.tenant = None
        with tenant_context(tenant):
            DummyModel(name="No exception please").save()

        connection.tenant = None
        with schema_context(tenant.schema_name):
            DummyModel(name="Survived it!").save()


class SharedAuthTest(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(SharedAuthTest, cls).setUpClass()
        settings.SHARED_APPS = ('tenant_schemas',
                                'django.contrib.auth',
                                'django.contrib.contenttypes', )
        settings.TENANT_APPS = ('dts_test_app', )
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        Tenant(domain_url='test.com', schema_name=get_public_schema_name()).save()

        # Create a tenant
        cls.tenant = Tenant(domain_url='tenant.test.com', schema_name='tenant')
        cls.tenant.save()

        # Create some users
        with schema_context(get_public_schema_name()):  # this could actually also be executed inside a tenant
            cls.user1 = User(username='arbitrary-1', email="arb1@test.com")
            cls.user1.save()
            cls.user2 = User(username='arbitrary-2', email="arb2@test.com")
            cls.user2.save()

        # Create instances on the tenant that point to the users on public
        with tenant_context(cls.tenant):
            cls.d1 = ModelWithFkToPublicUser(user=cls.user1)
            cls.d1.save()
            cls.d2 = ModelWithFkToPublicUser(user=cls.user2)
            cls.d2.save()

    def test_direct_relation_to_public(self):
        """
        Tests that a forward relationship through a foreign key to public from a model inside TENANT_APPS works.
        """
        with tenant_context(self.tenant):
            self.assertEqual(User.objects.get(pk=self.user1.id),
                             ModelWithFkToPublicUser.objects.get(pk=self.d1.id).user)
            self.assertEqual(User.objects.get(pk=self.user2.id),
                             ModelWithFkToPublicUser.objects.get(pk=self.d2.id).user)

    def test_reverse_relation_to_public(self):
        """
        Tests that a reverse relationship through a foreign keys to public from a model inside TENANT_APPS works.
        """
        with tenant_context(self.tenant):
            users = User.objects.all().select_related().order_by('id')
            self.assertEqual(ModelWithFkToPublicUser.objects.get(pk=self.d1.id),
                             users[0].modelwithfktopublicuser_set.all()[:1].get())
            self.assertEqual(ModelWithFkToPublicUser.objects.get(pk=self.d2.id),
                             users[1].modelwithfktopublicuser_set.all()[:1].get())


class TenantTestCaseTest(BaseTestCase, TenantTestCase):
    """
    Tests that the tenant created inside TenantTestCase persists on
    all functions.
    """

    def test_tenant_survives_after_method1(self):
        # There is one tenant in the database, the one created by TenantTestCase
        self.assertEquals(1, get_tenant_model().objects.all().count())

    def test_tenant_survives_after_method2(self):
        # The same tenant still exists even after the previous method call
        self.assertEquals(1, get_tenant_model().objects.all().count())
