import logging
import os.path
import re

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponse, HttpResponseServerError, \
    HttpResponseForbidden
from django.template import Context
from django.shortcuts import render_to_response

from tardis.tardis_portal import models
from tardis.tardis_portal.auth import auth_service
from tardis.tardis_portal.auth.localdb_auth import django_user, django_group

from mecat.vbl_auth import auth_key as vbl_auth_key
from mecat.forms import RegisterMetamanForm


logger = logging.getLogger('tardis.mecat')

_config = {}
_config['Echidna'] = {
    'expSchema': 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21',
    'dsSchema': 'http://gendsschema.com/',
    'dfSchema': 'http://www.tardis.edu.au/schemas/ansto/ech/2011/06/21',
    # accept OPUS files, which end with a number, and SPA and SPC files
    'filetypes': re.compile('.*\.(pdf)$|.*\.(hdf)$', re.IGNORECASE),
    # group all file which have the same basename into a dataset
    #'groupDSRules': ['directory', 1],
    'groupDSRules': ['sample'], 
    'metadata': None,
    'beamline_group': 'BEAMLINE_ECH',
    'sampleSchema': 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21',
    'chemicalSchema': 'http://www.tardis.edu.au/schemas/ansto/chemical/2011/06/21',
}

_config['Kowari'] = {
    'expSchema': 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21',
    'dsSchema': 'http://gendsschema.com/',
    'dfSchema': 'http://www.tardis.edu.au/schemas/ansto/kwr/2011/06/21',
    # accept OPUS files, which end with a number, and SPA and SPC files
    'filetypes': re.compile('.*\.(pdf)$|.*\.(hdf)$', re.IGNORECASE),
    # group all file which have the same basename into a dataset
    #'groupDSRules': ['directory', 1],
    'groupDSRules': ['sample'], 
    'metadata': None,
    'beamline_group': 'BEAMLINE_KWR',
    'sampleSchema': 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21',
    'chemicalSchema': 'http://www.tardis.edu.au/schemas/ansto/chemical/2011/06/21',
}

_config['Platypus'] = {
    'expSchema': 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21',
    'dsSchema': 'http://gendsschema.com/',
    'dfSchema': 'http://www.tardis.edu.au/schemas/ansto/plp/2011/06/21',
    # accept OPUS files, which end with a number, and SPA and SPC files
    'filetypes': re.compile('.*\.(pdf)$|.*\.(hdf)$', re.IGNORECASE),
    # group all file which have the same basename into a dataset
    #'groupDSRules': ['directory', 1],
    'groupDSRules': ['sample'], 
    'metadata': None,
    'beamline_group': 'BEAMLINE_PLP',
    'sampleSchema': 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21',
    'chemicalSchema': 'http://www.tardis.edu.au/schemas/ansto/chemical/2011/06/21',
}

_config['Quokka'] = {
    'expSchema': 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21',
    'dsSchema': 'http://gendsschema.com/',
    'dfSchema': 'http://www.tardis.edu.au/schemas/ansto/qkk/2011/06/21',
    # accept OPUS files, which end with a number, and SPA and SPC files
    'filetypes': re.compile('.*\.(pdf)$|.*\.(hdf)$', re.IGNORECASE),
    # group all file which have the same basename into a dataset
    #'groupDSRules': ['directory', 1],
    'groupDSRules': ['sample'], 
    'metadata': None,
    'beamline_group': 'BEAMLINE_QKK',
    'sampleSchema': 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21',
    'chemicalSchema': 'http://www.tardis.edu.au/schemas/ansto/chemical/2011/06/21',
}

_config['Wombat'] = {
    'expSchema': 'http://www.tardis.edu.au/schemas/ansto/experiment/2011/06/21',
    'dsSchema': 'http://gendsschema.com/',
    'dfSchema': 'http://www.tardis.edu.au/schemas/ansto/wbt/2011/06/21',
    # accept OPUS files, which end with a number, and SPA and SPC files
    'filetypes': re.compile('.*\.(pdf)$|.*\.(hdf)$', re.IGNORECASE),
    # group all file which have the same basename into a dataset
    #'groupDSRules': ['directory', 1],
    'groupDSRules': ['sample'], 
    'metadata': None,
    'beamline_group': 'BEAMLINE_WBT',
    'sampleSchema': 'http://www.tardis.edu.au/schemas/ansto/sample/2011/06/21',
    'chemicalSchema': 'http://www.tardis.edu.au/schemas/ansto/chemical/2011/06/21',
}


class Datafile():
    '''
    class to hold the parsed metadata about a datafile
    '''
    def __init__(self, name):
        # holds the metadata as ParameterName-Value(s)
        # TODO: used ordered dictionaries once we switched to Python 2.7
        self.data = {}
        # the name of the datafile
        self.name = name
        # the file size
        self.size = 0

    def __setitem__(self, key, value):
        # File size
        if key == 'File Size':
            self.size = value.replace(' bytes', '')
        else:
            key = key.replace(' ', '').replace('/', '')
            if key in self.data:
                self.data[key].append(value)
            else:
                self.data[key] = [value]

    def __getitem__(self, key):
        return self.data[key]

    def __len__(self):
        return len(self.data)

    def __delitem__(self, key):
        del self.data[key]

    def getSize(self):
        return self.size

    def getProtocol(self):
        return 'vbl'

    def hasMetadata(self):
        if len(self.data) > 0:
            return True
        else:
            return False

class DatasetMetadata():
    def __init__(self):
        self.data = {}
    def __setitem__(self, key, value):
        self.data[key] = value
    def __getitem__(self, key):
        return self.data[key]
    def __len__(self):
        return len(self.data)
    def __delitem__(self, key):
        del self.data[key]

def _acceptFile(name, beamline):
    '''
    Filter unknown file types for a particular beamline.

    Arguments:
    name -- filename
    beamline -- beamline short name
    '''
    basename = os.path.basename(name)
    pattern = _config[beamline]['filetypes']
    match = pattern.match(basename)
    if match is not None:
        return True
    else:
        return False


def _isDatasetMetadata(df, beamline):
    '''
    Dataset metadata is also stored in a file. This function decided
    whether the metadata belongs to the file itself or the
    corresponding dataset.

    Arguments:
    df -- Datafile object
    beamline -- beamline short name
    '''

    basename = os.path.basename(df.name)
    pattern = _config[beamline]['metadata']
    if pattern is not None:
        match = pattern.match(basename)
        if match is not None:
            return True

    return False


def _getDatasetName(df, beamline):
    '''
    Determines the dataset name for particular datafile and therefore
    the grouping of files into datasets.

    Arguments:
    df -- Datafile object
    beamline -- beamline short name

    '''
    ds_rule = _config[beamline]['groupDSRules'][0]

    # group by file patterns
    if ds_rule == 'file':
        # split by separator (usually '.' or '_')
        return df.name.rsplit(_config[beamline]['groupDSRules'][1], 1)[0]

    elif ds_rule == 'directory':
        item = _config[beamline]['groupDSRules'][1]
        tokens = df.name.split('/')
        return tokens[item]
    # group by sample_name  
    elif ds_rule == 'sample':
        # name will default to the directory name if
        # no sample is specified
        try:
            name =  df['sample_name'][0]       
        except KeyError:
            name = df.name.split('/')[1]
        return name
    else:
        return df.name


# TODO: date handeling!
def _save_parameters(schema, parameterset, data):
    """
    save all parameters into the database
    """

    parset = type(parameterset).__name__
    partype = parset.rstrip('Set')

    for key in data.keys():
        try:
            name = models.ParameterName.objects.get(schema=schema,
                                                    name__iexact=key)
            for item in data[key]:
                if partype == 'DatafileParameter':
                    parameter = models.DatafileParameter(parameterset=parameterset,
                                                         name=name)
                elif partype == 'DatasetParameter':
                    parameter = models.DatasetParameter(parameterset=parameterset,
                                                         name=name)
                elif partype == 'ExperimentParameter':
                    parameter = models.ExperimentParameter(parameterset=parameterset,
                                                           name=name)
                else:
                    raise ObjectDoesNotExist

                if name.data_type == models.ParameterName.NUMERIC:
                    try:
                        # remove possible units
                        tokens = item.split(' ')
                        if len(tokens) > 1:
                            units = tokens[1]
                        value = tokens[0]
                        numerical_value = float(value)
                        # TODO: make sure that unit matches!
                    except:
                        logger.exception('%s : %s ' % (key, item))
                    parameter.numerical_value = numerical_value
                else:
                    parameter.string_value = item
                try:
                    parameter.save()
                except:
                    logger.exception('%s %s : %s not saved!' % (parset, key, item))

        except models.ParameterName.DoesNotExist:
            logger.exception('Parameter %s not found in %s' % (key, schema.namespace))


# transaction-controlled!!!
@transaction.commit_on_success()
def _parse_metaman(request, cleaned_data):
    '''
    The actual parser which is called by the register function. The
    parser reads the raw metaman output (basically text
    files). Metaman prints the metadata for each file in consecutive
    blocks and one line for each key-value pair separated by ' : '.
    Files are separated by double line-breaks.

    The function contains a lot of logic which might not be documented
    elsewhere. The way the metadata is parsed might not be the most
    clever approach and should have been properly designed at the
    first place.

    :keyword request: Django HttpRequest instance
    :keyword cleaned_data: cleaned form fields
    '''

    # which beamline/instrument did it come from?
    beamline = cleaned_data['beamline']
    epn = cleaned_data['epn']

    ###
    ### I: Parse MetaMan ouput, loop over individual metadata blocks
    ###

    # the current Datafile object (if identified)
    df = None

    # list of Datafile objects (which holds the datafile metadata)
    files = []

    # that's the actual MetaMan upload
    metaman = request.FILES['metaman']
    logger.debug("Metaman file '%s' uploaded. Size: %i bytes"
                 % (metaman.name, metaman.size))

    # Save the metaman file for debugging for now
    tmpfn = os.path.join('/tmp', metaman.name)
    tmpfile = open(tmpfn, 'w')
    for chunk in metaman.chunks():
        tmpfile.write(chunk)
    metaman.seek(0)
    tmpfile.close()

    sample = None
    if 'sample' in request.FILES:
        sample = request.FILES['sample']
        logger.info("Sample information received. Size %i bytes" % sample.size)
        # Save the sample file for debugging for now
        tmpfn = os.path.join('/tmp', 's'+str(epn)+'.txt')
        tmpfile = open(tmpfn, 'w')
        for chunk in sample.chunks():
            tmpfile.write(chunk)
        metaman.seek(0)
        tmpfile.close()

    if not beamline in _config:
        logger.error("Unknown beamline key '%s'" % beamline)
        logger.error("No data will be commited to the database!")
        return HttpResponseServerError()


    # create experiment with info from post
    # check if experiment already exists
    # if so, run in 'update' rather then 'create' mode
    try:
        experiment = models.Experiment.objects.get(experimentparameterset__experimentparameter__string_value=epn, 
                                                   experimentparameterset__experimentparameter__name__name='EPN')
        update = True
        logger.debug('experiment with epn %s alreadt exists' % epn)
        logger.debug('- ingesting is being run in UPDATE mode')
        logger.debug('- all parametersets will be re-created, acls will not be touched')
    except models.Experiment.DoesNotExist:
        experiment = models.Experiment()
        update = False
        logger.debug('ingesting is being run in CREATE mode')

    experiment.title = cleaned_data['title']
    experiment.institution_name = cleaned_data['institution_name']
    experiment.description = cleaned_data['description']
    experiment.created_by = request.user
    experiment.start_time = cleaned_data['start_time']
    experiment.end_time = cleaned_data['end_time']
    experiment.save()
    logger.debug('experiment %i saved' % experiment.id)

    order = 0
    if update:
        models.Author_Experiment.objects.filter(experiment=experiment).delete()
        
    author_experiment = models.Author_Experiment(experiment=experiment,
                                                 author=cleaned_data['experiment_owner'],
                                                 order=order)
    author_experiment.save()
    order += 1
    for author in cleaned_data['researchers'].split(' ~ '):
        if author == '':
            continue
        logger.debug('adding author %s' % author)
        author_experiment = models.Author_Experiment(experiment=experiment,
                                                     author=author,
                                                     order=order)
        author_experiment.save()
        order += 1

    # additional experiment metadata
    exp_schema = \
        models.Schema.objects.get(namespace__exact=_config[beamline]['expSchema'])
    if update:
        models.ExperimentParameterSet.objects.filter(schema=exp_schema, 
                                                     experiment=experiment).delete()
    exp_parameterset = models.ExperimentParameterSet(schema=exp_schema,
                                                     experiment=experiment)
    exp_parameterset.save()

    experiment_metadata = {'beamline': cleaned_data['beamline'],
                           'epn': epn}
    if cleaned_data['program_id']:
        experiment_metadata['program_id'] = cleaned_data['program_id']

    for key, value in experiment_metadata.iteritems():
        try:
            exp_parameter = models.ParameterName.objects.get(schema=exp_schema,
                                                             name__iexact=key)
            exp_par = models.ExperimentParameter(parameterset=exp_parameterset,
                                                 name=exp_parameter,
                                                 string_value=value)
            exp_par.save()

        except models.ParameterName.DoesNotExist:
            logger.error('parameter %s not found in %s' % (key, exp_schema))

    if sample:
        # parse sample information and store it right away to keep the
        # order of the parameters
        sample_schema = \
            models.Schema.objects.get(namespace__exact=_config[beamline]['sampleSchema'])
        chemical_schema = \
            models.Schema.objects.get(namespace__exact=_config[beamline]['chemicalSchema'])

        if update:
            models.ExperimentParameterSet.objects.filter(schema=sample_schema,
                                                      experiment=experiment).delete()
            models.ExperimentParameterSet.objects.filter(schema=chemical_schema,
                                                      experiment=experiment).delete()

        sample_ps = None
        chemical_ps = None
        for line in sample:
            line = line.rstrip('\n')
            if line == '':
                continue
            key, value = line.split(' : ')

            if key == 'SampleDescription' or sample_ps is None:
                sample_ps = models.ExperimentParameterSet(
                    schema=sample_schema,
                    experiment=experiment)
                sample_ps.save()
                chemical_ps = None
            elif key == 'ChemicalName':
                chemical_ps = models.ExperimentParameterSet(
                    schema=chemical_schema,
                    experiment=experiment)
                chemical_ps.save()

            if value == '':
                continue

            # Use the chemical parameterset if one is active, otherwise just
            # use the current sample parameterset.
            paramset = chemical_ps or sample_ps
            try:
                param_name = models.ParameterName.objects.get(
                        schema=paramset.schema,
                        name__iexact=key)
                sample_par = models.ExperimentParameter(parameterset=paramset,
                                                        name=param_name,
                                                        string_value=value)
                sample_par.save()
            except models.ParameterName.DoesNotExist:
                logger.error('Parameter %s not found in schema %s' % (key, paramset.schema))

    # now parser the very intelligent metaman file
    for line in metaman:
        # remove newline
        line = line.rstrip('\n')
        # found a new metadata block?
        # <b>/Frames/Pilatus2_1m/Rotations/Tilt_SiCNTPDMScom20_CR_0001.tif</b>:
        if line[0:3] == '<b>' and line[-5:] == '</b>:':
            path = line[4:-5]
            # Do we accept this particular file type?
            if _acceptFile(path, beamline):
                # create new Datafile object and add it to the list
                df = Datafile(path)
                files += [df]
        elif line == '':
            # empty line indicates the end of current file metadata block
            df = None
        elif df is not None:
            # anything else is metadata
            try:
                token = line.split(' : ', 1)
                if len(token) > 1:
                    key, value = token[0], token[1]
                    df[key] = value
            except:
                # something went wrong?
                logger.exception(line)

    logger.debug('Parsing done')

    ###
    ### II: Build datasets from files: At this point all the metadata
    ### (apart from possible images) is memory but this is still
    ### better than doing it in a PHP script ...
    ###

    # holds files associated to a particular dataset
    datasets = {}

    # holds metadata information about the dataset
    metadata = {}

    # loop over datafiles
    for df in files:
        if not df.hasMetadata():
            continue
        # work out the dataset name
        dsName = _getDatasetName(df, beamline)
        metadata[dsName] = DatasetMetadata()
        metadata[dsName].data = {'sample_name': [dsName]}
        if not _isDatasetMetadata(df, beamline):
            # usual datafile metadata
            if not dsName in datasets:
                datasets[dsName] = [df]
            else:
                datasets[dsName].append(df)
        else:
            # this file holds metadata about the dataset!
            metadata[dsName] = df

    logger.debug('Grouping done')

    ###
    ### III: Ingest into database
    ###

    # loop over datasets
    for dsName, ds in datasets.items():
        description = dsName.replace('Data/', '')
        if update:
            try:
                dataset = models.Dataset.objects.get(experiment=experiment,
                                                     description=description)
            except models.Dataset.DoesNotExist:
                dataset = models.Dataset(experiment=experiment,
                                         description=description)
                dataset.save()
        else:
            dataset = models.Dataset(experiment=experiment,
                                     description=description)
            dataset.save()

        # does this dataset have any metadata?
        if dsName in metadata.keys():
            ds_schema = models.Schema.objects.get(namespace__exact=_config[beamline]['dsSchema'])
            if update:
                try:
                    models.DatasetParameterSet.objects.get(schema=ds_schema,
                                                           dataset=dataset).delete()
                except models.DatasetParameterSet.DoesNotExist:
                    pass  # nothing to delete


            ds_parameterset = models.DatasetParameterSet(schema=ds_schema,
                                                         dataset=dataset)
            ds_parameterset.save()

            _save_parameters(ds_schema, ds_parameterset, metadata[dsName].data)

        # loop over associated files
        df_schema = \
            models.Schema.objects.get(namespace__exact=_config[beamline]['dfSchema'])

        for df in ds:
            if update:
                try:
                    dataset_file = models.Dataset_File.objects.get(dataset=dataset,
                                                                    url='vbl://' + df.name,
                                                                    protocol='vbl')
                    dataset_file.size=df.getSize()
                except models.Dataset_File.DoesNotExist:
                    dataset_file = models.Dataset_File(dataset=dataset,
                                                       filename=os.path.basename(df.name),
                                                       url='vbl://' + df.name,
                                                       size=df.getSize(),
                                                       protocol='vbl')
            else:
                dataset_file = models.Dataset_File(dataset=dataset,
                                                   filename=os.path.basename(df.name),
                                                   url='vbl://' + df.name,
                                                   size=df.getSize(),
                                                   protocol='vbl')
            dataset_file.save()

            # loop over file meta-data
            if update:
                models.DatafileParameterSet.objects.get(schema=df_schema,
                                                        dataset_file=dataset_file).delete()

            df_parameterset = models.DatafileParameterSet(schema=df_schema,
                                                          dataset_file=dataset_file)
            df_parameterset.save()

            _save_parameters(df_schema, df_parameterset, df.data)

    logger.debug('Ingestion done')

    ###
    ### IV: Setup permissions (for users and groups)
    ###
    if update:
        logger.debug('update mode, experiment acls will not be touched')
        return experiment.id

## Removed experiment owner user creation code until EPN->ADuser lookup is
## possible.
##
#    owners = cleaned_data['experiment_owner'].split(' ~ ')
#    for owner in owners:
#        if owner == '':
#            continue
#        logger.debug('looking for owner %s' % owner)
#        # find corresponding user
#        user = auth_service.getUser({'pluginname': vbl_auth_key,
#                                    'id': owner})
#
#       logger.debug('registering user %s for owner %s' % (user.username, owner))
#       acl = models.ExperimentACL(experiment=experiment,
#                                  pluginId=django_user,
#                                  entityId=str(user.id),
#                                  isOwner=True,
#                                  canRead=True,
#                                  canWrite=True,
#                                  canDelete=True,
#                                  aclOwnershipType=models.ExperimentACL.OWNER_OWNED)
#       acl.save()
##


    beamline_group = _config[beamline]['beamline_group']
    group, created = Group.objects.get_or_create(name=beamline_group)

    if created:
        logger.debug('registering new group: %s' % group.name)
    else:
        logger.debug('registering existing group: %s' % group.name)

    # beamline group
    acl = models.ExperimentACL(experiment=experiment,
                               pluginId=django_group,
                               entityId=str(group.id),
                               canRead=True,
                               aclOwnershipType=models.ExperimentACL.SYSTEM_OWNED)
    acl.save()

    # create vbl group
    acl = models.ExperimentACL(experiment=experiment,
                               pluginId='vbl_group',
                               entityId=cleaned_data['epn'],
                               canRead=True,
                               aclOwnershipType=models.ExperimentACL.SYSTEM_OWNED)
    acl.save()

    # finally, always add acl for admin group
    group, created = Group.objects.get_or_create(name='admin')
    acl = models.ExperimentACL(experiment=experiment,
                               pluginId=django_group,
                               entityId=str(group.id),
                               isOwner=True,
                               canRead=True,
                               aclOwnershipType=models.ExperimentACL.SYSTEM_OWNED)
    acl.save()

    return experiment.id


def register_metaman(request):
    '''
    view function to handle the MetaMan file upload
    '''

    if request.method == 'POST':
        form = RegisterMetamanForm(request.POST, request.FILES)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            epn = form.cleaned_data['epn']

            logger.info('=== ingestion request for epn %s' % epn)

            user = authenticate(username=username, password=password)
            if user is None:
                logger.debug('authorisation failed')
                response = HttpResponseForbidden()
                response.write('authorization failed')
                return response
            elif user.is_active is False:
                logger.debug('user account %s is inactive' % user.username)
                response = HttpResponseForbidden()
                response.write('authorization failed')
                return response
            else:
                login(request, user)

                try:
                    logger.info('calling _parse_metaman for epn %s' % epn)
                    expid = _parse_metaman(request, form.cleaned_data)
                    logger.info('_parse_metaman SUCCESS,'
                                ' experiment id = %i' % expid)
                except:
                    logger.exception('exception')
                    logger.error('=== ingesting for epn %s FAILED' % epn)
                    return HttpResponseServerError()

                logger.info('=== ingestion FINISHED for epn %s' % epn)
                logout(request)

                return HttpResponse(str(expid))

        c = Context({'form': form,
                     'error': True,
                     'header': 'Register Metaman File'})
        render_to_response('tardis_portal/form_template.html', c)

    else:
        form = RegisterMetamanForm()

    c = Context({'form': form,
                 'header': 'Register Metaman File'})
    return render_to_response('tardis_portal/form_template.html', c)
