"""
    management utility to create the custom embargo permission for ANSTO's MeCAT application
"""

import sys

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission, ContentType


from datetime import datetime as dt


class Command(BaseCommand):

    help = 'Create embargo_admin permission'

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))

        content_type, _ = ContentType.objects.get_or_create(model='', app_label='mecat')
        permission, _ = Permission.objects.get_or_create(codename='embargo_admin', name='Embargo Administrator', content_type=content_type)
