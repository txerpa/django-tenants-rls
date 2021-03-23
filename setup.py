#!/usr/bin/env python

from os.path import exists

from setuptools import setup

from version import get_git_version

setup(
    name='django-tenant-schemas',
    version=get_git_version(),
    author='Bernardo Pires Carneiro',
    author_email='carneiro.be@gmail.com',
    packages=[
        'tenant_schemas',
        'tenant_schemas.contrib',
        'tenant_schemas.contrib.drf',
        'tenant_schemas.postgresql_backend',
        'tenant_schemas.management',
        'tenant_schemas.management.commands',
        'tenant_schemas.templatetags',
        'tenant_schemas.test',
        'tenant_schemas.tests',
    ],
    scripts=[],
    url='https://github.com/bcarneiro/django-tenant-schemas',
    license='MIT',
    description='Tenant support for Django using PostgreSQL RLS.',
    long_description=open('README.rst').read() if exists('README.rst') else '',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Framework :: Django',
        'Framework :: Django :: 2.2.3',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.8',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries',
    ],
    install_requires=[
        'Django>=2.2',
        'psycopg2',
    ],
    zip_safe=False,
)
