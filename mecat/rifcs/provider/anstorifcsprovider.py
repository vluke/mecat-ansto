from django.template import Context 
from tardis.tardis_portal.models import ExperimentParameter, ParameterName, Schema  

import tardis.tardis_portal.publish.provider.schemarifcsprovider as schemarifcsprovider
    
SERVER_URL = "https://mecat-test.nbi.ansto.gov.au"
HARVEST_URL = "http://mecat-test.nbi.ansto.gov.au:8080/oai/provider"

INSTRUMENT_SERVICE_IDS = {
    'Echidna' : '766',
    'Kowari' : '767',
    'Platypus' : '768',
    'Quokka' : '769',
    'Wombat' : '770'
    }
    
class AnstoRifCsProvider(schemarifcsprovider.SchemaRifCsProvider):      
    
    def __init__(self):
        super(AnstoRifCsProvider, self).__init__()
        self.namespace = 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21'  
        self.sample_desc_schema_ns = 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21'
      
    def get_email(self, beamline):
        return "%s@ansto.gov.au" % beamline
        
    def get_originating_source(self):
        return HARVEST_URL
        
    def get_key(self, experiment):
        return "research-data.ansto.gov.au/collection/bragg/%s" % (experiment.id)  
         
    def get_produced_by(self, beamline):
        return 'research-data.ansto.gov.au/collection/%s' % \
            INSTRUMENT_SERVICE_IDS[beamline]

    def get_rights(self, experiment):
        if self.get_license_uri(experiment):
            return []
        return [('This information is supplied on the condition that the '
                'primary investigators are credited in any publications '
                'that use the data.')]

    def get_access_rights(self, experiment):
        if self.get_license_uri(experiment):
            return []
        return [('This collection of data is released as-is. Where data is '
                'publicly accessible, data will no longer be subject to embargo '
                'and can be used freely provided attribution for the source is '
                'given. It is encouraged that persons interested in using the '
                'data contact the parties listed for this record to obtain '
                'guidance and context in applying this data set and to stay '
                'informed about upcoming revisions and related releases of '
                'interest.')]

    def get_rifcs_context(self, experiment):
        c = super(AnstoRifCsProvider, self).get_rifcs_context(experiment)
        beamline = self.get_beamline(experiment)
        c['originating_source'] = self.get_originating_source()
        c['email'] = self.get_email(beamline)
        c['key'] = self.get_key(experiment)
        c['url'] = self.get_url(experiment, SERVER_URL)
        c['produced_by'] = self.get_produced_by(beamline)
        c['anzsrcfor'].extend(['029904'])
        c['rights'] = self.get_rights(experiment)
        c['access_rights'] = self.get_access_rights(experiment)
        return c