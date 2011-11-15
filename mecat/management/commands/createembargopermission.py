"""
    management utility to create the custom embargo permission for ANSTO's MeCAT application
"""

import sys

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType


class Command(BaseCommand):

    help = 'Create embargo_admin permission'

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))

        content_type, _ = ContentType.objects.get_or_create(model='experiment', app_label='tardis_portal')
        permission, _ = Permission.objects.get_or_create(codename='embargo_admin', name='Embargo Administrator', content_type=content_type)
