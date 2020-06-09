from django.conf import settings
from django.db.models.base import ModelBase
from django.db.utils import load_backend


# TODO: configure a router to use superuser for administrative tasks
class TenantAdminRouter(object):
    """
    A router to control which applications will be synced,
    depending if we are syncing the shared apps or the tenant apps.
    """
    pass
