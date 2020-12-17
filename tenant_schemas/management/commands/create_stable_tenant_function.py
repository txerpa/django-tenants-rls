
from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):

    help = 'Command creates stable function with a very high cost which returns tenant from the current settings.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute('CREATE OR REPLACE FUNCTION get_current_tenant() RETURNS VARCHAR AS $$ '
                           'SELECT current_setting(\'txerpa.tenant\') '
                           '$$ LANGUAGE SQL STABLE COST 100000;')
