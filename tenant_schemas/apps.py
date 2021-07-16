import logging

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Critical, Error, Warning, register
from django.core.files.storage import default_storage
from django.db.models.signals import pre_migrate
from django.core.management import call_command

from .contrib.drf.utils import is_bad_tenant_field_config
from .storage import TenantStorageMixin

logger = logging.getLogger()


def create_or_replace_pg_get_tenant_function(sender, **kwargs):
    logger.info("running create_stable_tenant_function command...")
    call_command('create_stable_tenant_function')
    logger.info("OK")


class TenantSchemaConfig(AppConfig):
    name = 'tenant_schemas'

    def ready(self):
        pre_migrate.connect(create_or_replace_pg_get_tenant_function, sender=self)
        self.configure_external_models()

    def configure_external_models(self):
        from .models import MultitenantMixin, generate_rls_fk_field

        tenant_apps_set = set(settings.TENANT_APPS)

        for app in self.apps.all_models.keys():
            app_config = self.apps.app_configs[app]
            if app_config.name in tenant_apps_set:
                for model_name, model in app_config.models.items():
                    if not issubclass(model, MultitenantMixin):
                        # tenant field name is also hardcoded in tenant_schemas.models.MultitenantMixin
                        model.add_to_class('tenant', generate_rls_fk_field())


@register('config')
def best_practice(app_configs, **kwargs):
    """
    Test for configuration recommendations. These are best practices, they
    avoid hard to find bugs and unexpected behaviour.
    """
    if app_configs is None:
        app_configs = apps.get_app_configs()

    # Take the app_configs and turn them into *old style* application names.
    # This is what we expect in the SHARED_APPS and TENANT_APPS settings.
    installed_apps = [config.name for config in app_configs]

    warnings = list()
    errors = list()

    # Critical
    if not hasattr(settings, 'TENANT_APPS'):
        return [Critical('TENANT_APPS setting not set', obj="django.conf.settings", id="tenant_schemas.C001")]

    if not hasattr(settings, 'TENANT_MODEL'):
        return [Critical('TENANT_MODEL setting not set', obj="django.conf.settings", id="tenant_schemas.C002")]

    if not hasattr(settings, 'SHARED_APPS'):
        return [Critical('SHARED_APPS setting not set', obj="django.conf.settings", id="tenant_schemas.C003")]

    # Errors
    if not settings.TENANT_APPS:
        errors.append(
            Error("TENANT_APPS is empty.",
                  hint="Maybe you don't need this app?",
                  id="tenant_schemas.E001"))

    if not set(settings.TENANT_APPS).issubset(installed_apps):
        delta = set(settings.TENANT_APPS).difference(installed_apps)
        errors.append(
            Error("You have TENANT_APPS that are not in INSTALLED_APPS",
                  hint=[a for a in settings.TENANT_APPS if a in delta],
                  id="tenant_schemas.E002"))

    if not set(settings.SHARED_APPS).issubset(installed_apps):
        delta = set(settings.SHARED_APPS).difference(installed_apps)
        errors.append(
            Error("You have SHARED_APPS that are not in INSTALLED_APPS",
                  hint=[a for a in settings.SHARED_APPS if a in delta],
                  id="tenant_schemas.E003"))

    # Warnings
    django_index = next(i for i, s in enumerate(installed_apps) if s.startswith('django.'))
    if installed_apps.index('tenant_schemas') > django_index:
        warnings.append(
            Warning("You should put 'tenant_schemas' before any django "
                    "core applications in INSTALLED_APPS.",
                    obj="django.conf.settings",
                    hint="This is necessary to overwrite built-in django "
                         "management commands with their schema-aware "
                         "implementations.",
                    id="tenant_schemas.W001"))

    if not settings.SHARED_APPS:
        warnings.append(
            Warning("SHARED_APPS is empty.",
                    id="tenant_schemas.W002"))

    if not isinstance(default_storage, TenantStorageMixin):
        warnings.append(Warning(
            "Your default storage engine is not tenant aware.",
            hint="Set settings.DEFAULT_FILE_STORAGE to 'tenant_schemas.storage.TenantFileSystemStorage' "
                 "or use custom one.",
            id="tenant_schemas.W003"
        ))

    return warnings + errors


@register('rest_framework.serializers')
def check_serializers(app_configs, **kwargs):
    import inspect
    from rest_framework.serializers import ModelSerializer as drf_ModelSerializer, HyperlinkedModelSerializer
    from rest_framework_json_api.serializers import ModelSerializer as json_api_ModelSerializer
    from .models import MultitenantMixin
    from .contrib.drf.serializers import RLSModelSerializer

    import config.urls  # noqa, force import of all serializers.

    for serializer in (
        drf_ModelSerializer.__subclasses__() +
        json_api_ModelSerializer.__subclasses__() +
        HyperlinkedModelSerializer.__subclasses__()
    ):
        # Skip third-party apps and serializers that have already RLSModelSerializer as base class.
        path = inspect.getfile(serializer)
        if path.find('site-packages') > -1 or issubclass(serializer, RLSModelSerializer):
            continue

        model = getattr(serializer.Meta, 'model')
        if issubclass(model, MultitenantMixin) and is_bad_tenant_field_config(serializer):
            yield Warning(
                f'{serializer.__name__} use a MultitenantMixin based model, but don\'t ignore tenant field, '
                f'this may cause performance issues.',
                hint=f'Add {RLSModelSerializer.__name__} to {serializer.__name__} serializer',
                obj=serializer,
                id='tenant_schemas.W004',
            )
