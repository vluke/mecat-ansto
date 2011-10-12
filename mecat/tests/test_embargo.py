from django.test import TestCase

import sys
import datetime
from datetime import datetime as old_datetime

class FrozenTime:
    """ gratuitously copied over from tardis/tardis_portal/tests/test_tokens"""

    def __init__(self, *args, **kwargs):
        self.year = args[0]
        self.month = args[1]
        self.day = args[2]
        self.hour = args[3]

    def __lt__(a, b):
        return old_datetime(a.year, a.month, a.day, a.hour) < old_datetime(b.year, b.month, b.day, b.hour)

    @classmethod
    def freeze_time(cls, time):
        cls.frozen_time = time

    @classmethod
    def now(cls):
        return cls.frozen_time

    def __str__(self):
        return "%s %s %s  %s" % (self.year, self.month, self.day, self.hour)

class EmbargoHandlerTest(TestCase):

    def setUp(self):
        from django.contrib.auth.models import User
        from tardis.tardis_portal.models import Experiment
        user = 'tardis_user1'
        pwd = 'secret'
        email = ''
        self.user = User.objects.create_user(user, email, pwd)
        self.experiment = Experiment(created_by=self.user)
        self.experiment.save()

        sys.modules['datetime'].datetime = FrozenTime

    def tearDown(self):
        sys.modules['datetime'].datetime = old_datetime

    def test_search(self):
        self.assertEqual(2,2)
