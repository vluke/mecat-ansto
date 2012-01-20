from django.test import TestCase
from tardis.tardis_portal.models import User, Experiment
import mecat.rifcs.provider.anstorifcsprovider as anstorifcsprovider
from mecat.rifcs.provider.anstorifcsprovider import AnstoRifCsProvider
from tardis.apps.ands_register.publishing import PublishHandler

class AnstoRifCsProviderTestCase(TestCase):
    
    custom_description_key = 'custom_description'
    custom_authors_key = 'custom_authors'
    access_type_key = 'access_type'
    random_custom_description = 'a custom description'
    
    def setUp(self):
        self.user = User.objects.create_user(username='TestUser',
                                             email='user@test.com',
                                             password='secret')
        self.e1 = Experiment(id="1", title="Experiment 1", created_by=self.user, public=False)
        self.e1.save()
        self.provider = AnstoRifCsProvider()
        self.publish_data = { 
                    self.custom_authors_key: "",
                    self.custom_description_key: "",
                    self.access_type_key: "public"
                   }       
        
    
    def testInitialisation(self):
        self.assertIsNotNone(self.provider.namespace)
        self.assertIsNotNone(self.provider.sample_desc_schema_ns)
        
    def testCanPublishNotPublicAndUnpublished(self):
        # (experiment.public : False, access type : Unpublished) -> FALSE
        self.assertFalse(self.provider.can_publish(self.e1))
        
#    def testCanPublishNotPublicAndPublic(self):    
#        # (experiment public: False, access type: public) -> throw an exception
#        ph = PublishHandler(self.e1.id, create=True)
#        ph.update(self.publish_data)
#        self.assertFalse(self.provider.can_publish(self.e1))
      
    def testCanPublishNotPublicAndPrivate(self):  
        # (experiment public: False, access type: private) -> True
        self.publish_data[self.access_type_key] = "private"
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))
   
    def testCanPublishNotPublicAndMediated(self):     
        # (experiment public: False, access type: mediated) -> True
        self.publish_data[self.access_type_key] = "mediated"
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))     
        
    def testCanPublishPublicAndMediated(self):    
        # (experiment public: True, access type: mediated) -> True
        self.e1.public = True
        self.e1.save()
        self.publish_data[self.access_type_key] = "mediated"
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))
    
    def testCanPublishPublicAndPublished(self):
        # (experiment public: True, access type: published) -> True
        self.e1.public = True
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))
        
    def testCanPublishPublicAndPrivate(self):
        # (experiment public: True, access type: private) -> True
        self.e1.public = True
        self.publish_data[self.access_type_key] = "private"
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))    
        
    def testCanPublishPublicAndUnpublished(self):
        # (experiment public: True, access type: unpublished) -> False
        self.e1.public = True
        self.publish_data[self.access_type_key] = "unpublished"
        ph = PublishHandler(self.e1.id, create=True)
        ph.update(self.publish_data)
        self.assertTrue(self.provider.can_publish(self.e1))       
        
    def testEmail(self):
        emails = self.provider.get_emails(["mybeamline"])
        self.assertEquals(emails, ["mybeamline@ansto.gov.au"])
    
    def testOriginatingSource(self):
        orig_source = self.provider.get_originating_source()
        self.assertEquals(orig_source, anstorifcsprovider.HARVEST_URL)

    def testKey(self):
        key = self.provider.get_key(self.e1)
        self.assertEquals(key, "research-data.ansto.gov.au/collection/bragg/%s" % self.e1.id)
        
    def testProducedBy(self):
        prod_bys = self.provider.get_produced_bys(["Quokka"])
        self.assertEquals(prod_bys, ['research-data.ansto.gov.au/collection/769'])
        
    def testGetDescriptionEmpty(self):
        description = self.provider.get_description(self.e1)
        self.assertEquals(description, "")
        
    def testGetDescriptionCustom(self):
        ph = PublishHandler(self.e1.id, create=True)
        self.publish_data[self.custom_description_key] = self.random_custom_description
        ph.update(self.publish_data)
        self.assertEquals(self.random_custom_description, ph.custom_description())
        
        self.assertEquals(ph.custom_description(), self.random_custom_description)
        description = self.provider.get_description(self.e1)
        
        self.assertEquals(description, self.random_custom_description)
