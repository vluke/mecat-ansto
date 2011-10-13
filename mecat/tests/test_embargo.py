from django.test import TestCase
from django.conf import settings

import sys
import datetime as dt

from mecat.embargo import EmbargoHandler
from tardis.tardis_portal.models import Experiment


class EmbargoHandlerTest(TestCase):

    def setUp(self):
        from django.contrib.auth.models import User
        user = 'tardis_user1'
        pwd = 'secret'
        email = ''
        self.user = User.objects.create_user(user, email, pwd)


    def testCleanExperiment(self):
        experiment = Experiment(created_by=self.user)
        experiment.save()

        eh = EmbargoHandler(experiment.id)
        self.assertTrue(eh.never_expires())
        self.assertFalse(eh.has_any_expiry())
        self.assertFalse(eh.can_be_defaulted())
        self.assertTrue(eh.because_no_end_date())
        self.assertEqual(None, eh.get_expiry_date())

        self.assertRaises(Exception, eh.prevent_expiry)
        eh.reset_to_default()  # should not raise Exception
        self.assertRaises(Exception, eh.set_expiry)

    def testCleanExperimentWithEndDate(self):
        experiment = Experiment(created_by=self.user, end_time=dt.datetime(2011, 12, 31))
        experiment.save()

        expected_expiry = experiment.end_time + dt.timedelta(settings.EMBARGO_DAYS)

        eh = EmbargoHandler(experiment.id)
        self.assertFalse(eh.never_expires())
        self.assertTrue(eh.has_any_expiry())
        self.assertFalse(eh.can_be_defaulted())
        self.assertFalse(eh.because_no_end_date())
        self.assertEqual(expected_expiry, eh.get_expiry_date())

        self.assertRaises(Exception, eh.prevent_expiry)
        eh.reset_to_default()  # should not raise Exception
        self.assertRaises(Exception, eh.set_expiry)

    def testSetExpiry(self):
        expiry = dt.datetime(2034, 12, 4)
        expiry_as_string = '2034/12/04'
        
        experiment = Experiment(created_by=self.user)
        experiment.save()

        eh = EmbargoHandler(experiment.id)
        self.assertTrue(eh.never_expires())
        self.assertEqual(None, eh.get_expiry_date())

        eh = EmbargoHandler(experiment.id, True)
        eh.set_expiry(expiry_as_string)

        eh = EmbargoHandler(experiment.id)
        self.assertEqual(expiry, eh.get_expiry_date())

    def testResetToDefault(self):
        expiry = dt.datetime(2034,12,4)
        expiry_as_string = '2034/12/04'

        experiment = Experiment(created_by=self.user)
        experiment.save()
        eh = EmbargoHandler(experiment.id, True)
        eh.set_expiry(expiry_as_string)

        self.assertEqual(expiry, eh.get_expiry_date())

        eh = EmbargoHandler(experiment.id, True)
        eh.reset_to_default()

        self.assertEqual(None, eh.get_expiry_date())

    def testNeverExpire(self):
        experiment = Experiment(created_by=self.user, end_time=dt.datetime(1999,4,3))
        experiment.save()

        eh = EmbargoHandler(experiment.id, True)
        self.assertFalse(eh.never_expires())

        eh.prevent_expiry()
        self.assertTrue(eh.never_expires())
        self.assertFalse(eh.because_no_end_date())
