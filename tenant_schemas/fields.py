from django.db import models


class RLSForeignKey(models.ForeignKey):
    rls_required = True
