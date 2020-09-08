django-tenant-schemas
=====================

|PyPi version| |PyPi downloads| |Python versions| |Travis CI| |PostgreSQL|

This application enables `django`_ powered websites to have multiple
tenants via `PostgreSQL row-level security`_. A vital feature for every
Software-as-a-Service website.

Django provides currently no simple way to support multiple tenants
using the same project instance, even when only the data is different.
Because we don't want you running many copies of your project, you'll be
able to have:

-  Multiple customers running on the same instance
-  Shared and Tenant-Specific data
-  Tenant View-Routing

Why row-level security and not schemas
--------------------------------------

There are typically three solutions for solving the multitenancy
problem.

1. Isolated Approach: Separate Databases. Each tenant has it's own
   database.

2. Semi Isolated Approach: Shared Database, Separate Schemas. One
   database for all tenants, but one schema per tenant.

3. Shared Approach: Shared Database, Shared Schema. All tenants share
   the same database and schema. There is a main tenant-table, where all
   other tables have a foreign key pointing to.

This application implements the *third* approach, which in our opinion,
represents the ideal compromise between simplicity and performance.

We have being using dts for years with great pain, as tenant base grew was
nearly imposible to maintain, both due of the complexity of migrations wich
can endure for hours and the lack of a suitable backup when you have hundred
of thousands of tables, which can happen really fast when running a SaaS
service as txerpa.com.

So we've decided to fork django-tenant-schemas to maintain its goals.

-  Simplicity: barely make any changes to your current code to support
   multitenancy. Plus, you only manage one database.
-  Performance: make use of shared connections, buffers and memory.

DTS is better suited if you plan to have less than a hundred (or so) tenants
each one with tons of data. DTS is a great project that has been really usefull
for us, we love the simplicity of its API and the level of isolation it granted
to our project.

How it works
------------
TODO

What can this app do?
---------------------

As many tenants as you want
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each tenant has its data protected and database level with row-level security. Use a single project
instance to serve as many as you want.

Tenant-specific and shared models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tenant-specific apps do not share their data between tenants, but you
can also have shared models where the information is always available and
shared between all.

Tenant View-Routing
~~~~~~~~~~~~~~~~~~~

You can have different views for ``http://customer.example.com/`` and
``http://example.com/``, even though Django only uses the string after
the host name to identify which view to serve.

Magic
~~~~~

Everyone loves magic! You'll be able to have all this barely having to
change your code!

Setup & Documentation
---------------------

**This is just a short setup guide**, it is **strongly** recommended
that you read the complete version at
`django-tenant-schemas.readthedocs.io`_.

Your ``DATABASE_ENGINE`` setting needs to be changed to

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'tenant_schemas.postgresql_backend',
            # ..
        }
    }

Add the middleware ``tenant_schemas.middleware.TenantMiddleware`` to the
top of ``MIDDLEWARE_CLASSES``, so that each request can be set to use
the correct schema.

.. code-block:: python

    MIDDLEWARE_CLASSES = (
        'tenant_schemas.middleware.TenantMiddleware',
        #...
    )

Add ``tenant_schemas.routers.TenantSyncRouter`` to your `DATABASE_ROUTERS`
setting, so that the correct apps can be synced, depending on what's
being synced (shared or tenant).

.. code-block:: python

    DATABASE_ROUTERS = (
        'tenant_schemas.routers.TenantSyncRouter',
    )

Add ``tenant_schemas`` to your ``INSTALLED_APPS``.

Create your tenant model
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from django.db import models
    from tenant_schemas.models import TenantMixin

    class Client(TenantMixin, models.Model):
        name = models.CharField(max_length=100)
        paid_until =  models.DateField()
        on_trial = models.BooleanField()
        created_on = models.DateField(auto_now_add=True)

Define on ``settings.py`` which model is your tenant model. Assuming you
created ``Client`` inside an app named ``customers``, your
``TENANT_MODEL`` should look like this:

.. code-block:: python

    TENANT_MODEL = "customers.Client" # app.Model

Now run ``migrate_schemas`` to sync your apps to the ``public`` schema.

::

    python manage.py migrate_schemas --shared

Create your tenants just like a normal django model. Calling ``save``
will automatically create and sync/migrate the schema.

.. code-block:: python

    from customers.models import Client

    # create your public tenant
    tenant = Client(domain_url='tenant.my-domain.com',
                    schema_name='tenant1',
                    name='My First Tenant',
                    paid_until='2014-12-05',
                    on_trial=True)
    tenant.save()

Any request made to ``tenant.my-domain.com`` will now automatically set
your PostgreSQL's ``search_path`` to ``tenant1`` and ``public``, making
shared apps available too. This means that any call to the methods
``filter``, ``get``, ``save``, ``delete`` or any other function
involving a database connection will now be done at the tenant's schema,
so you shouldn't need to change anything at your views.

You're all set, but we have left key details outside of this short
tutorial, such as creating the public tenant and configuring shared and
tenant specific apps. Complete instructions can be found at
`django-tenant-schemas.readthedocs.io`_.


Logging
-------

You can configure logging as normal django app, add new logger for tenant_schemas app to loggers section, something like this:

.. code-block:: python

    LOGGING = {
        # ...

        'loggers': {
            # ...

            'tenant_schemas': {
                'handlers': ['file'],
                'level': 'DEBUG',
            }
        }
    }

Use handlers of your preference.


.. _django: https://www.djangoproject.com/
.. _PostgreSQL row-level security: https://www.postgresql.org/docs/11/ddl-rowsecurity.html
.. _PostgreSQL's official documentation on schemas: http://www.postgresql.org/docs/9.1/static/ddl-schemas.html
.. _Multi-Tenant Data Architecture: http://msdn.microsoft.com/en-us/library/aa479086.aspx

.. |PyPi version| image:: https://img.shields.io/pypi/v/django-tenant-schemas.svg
   :target: https://pypi.python.org/pypi/django-tenant-schemas
.. |PyPi downloads| image:: https://img.shields.io/pypi/dm/django-tenant-schemas.svg
   :target: https://pypi.python.org/pypi/django-tenant-schemas
.. |Python versions| image:: https://img.shields.io/pypi/pyversions/django-tenant-schemas.svg
.. |Travis CI| image:: https://travis-ci.org/bernardopires/django-tenant-schemas.svg?branch=master
   :target: https://travis-ci.org/bernardopires/django-tenant-schemas
.. |PostgreSQL| image:: https://img.shields.io/badge/PostgreSQL-9.2%2C%209.3%2C%209.4%2C%209.5%2C%209.6-blue.svg
.. _setup: https://django-tenant-schemas.readthedocs.io/en/latest/install.html
.. _django-tenant-schemas.readthedocs.io: https://django-tenant-schemas.readthedocs.io/en/latest/
