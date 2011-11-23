# -*- coding: utf-8 -*-

"""
download.py

@author Ulrich Felzmann

"""
import logging
from suds.client import Client

from django.conf import settings
from django.shortcuts import *
from django.http import HttpResponseNotFound
from django.template import Context

from tardis.tardis_portal import models
from tardis.tardis_portal.auth.decorators import *


logger = logging.getLogger('tardis.mecat')


class VBLDownload():
    def __init__(self, request):
        proxy = getattr(settings, 'VBLPROXY', None)
        # Switch the suds cache off, otherwise suds will try to
        # create a tmp directory in /tmp. If it already exists but
        # has the wrong permissions, the download will fail.
        self.client = Client(settings.VBLTARDISINTERFACE,
                             cache=None,
                             proxy=proxy)
        self.request = request

    def download(self, EPN, file_string=''):
        # No authentication is done beyond this point. The caller *must* have
        # already determined that the logged in user is authorized to access
        # the experiment in EPN and the files in file_string.
        logger.debug('VBL download request received for EPN %s. ' % EPN)
        key = self.client.service.VBLstartTransferSSL(EPN, file_string)
        if key.startswith('Error:'):
            logger.error('VBL download request failed: %s' % key)
            logger.error(file_string)
            return return_response_error(self.request)
        else:
            c = Context({'subtitle': 'Download',
                         'key': key,
                         'expid': EPN})
            return render_to_response('tardis_portal/vbl_download.html', c)


def download_datafile(request, datafile_id):

    datafile = models.Dataset_File.objects.get(pk=datafile_id)
    if not has_datafile_access(request, datafile_id):
        return return_response_error(request)

    par = models.ExperimentParameter.objects.filter(parameterset__experiment=
                                                    datafile.dataset.experiment)
    epn = par.get(name__name='EPN').string_value
    absolute_filename = datafile.url.partition('://')[2]
    file_string = absolute_filename + "\\r\\nTARDIS\\r\\n"
    download = VBLDownload(request)
    return download.download(epn, file_string)


def download_datafiles(request):

    if (len(request.POST.getlist('datafile')) == 0 \
        and len(request.POST.getlist('dataset')) == 0):

        response = HttpResponseNotFound()
        response.write('<p>No files selected!</p>\n')
        return response

    from string import atoi
    par = models.ExperimentParameter.objects.filter(parameterset__experiment=
                                                    atoi(request.POST.get('expid')))

    epn = par.get(name__name='EPN').string_value

    datafiles = request.POST.getlist('datafile')
    datasets = request.POST.getlist('dataset')

    file_string = ""
    for dsid in datasets:
        if has_dataset_access(request, dsid):
            for datafile in models.Dataset_File.objects.filter(dataset=dsid):
                absolute_filename = datafile.url.partition('://')[2]
                file_string += absolute_filename + "\\r\\nTARDIS\\r\\n"

    for dfid in datafiles:
        if has_datafile_access(request, dfid):
            datafile = models.Dataset_File.objects.get(pk=dfid)
            if not datafile.dataset.id in datasets:
                absolute_filename = datafile.url.partition('://')[2]
                file_string += absolute_filename + "\\r\\nTARDIS\\r\\n"

    download = VBLDownload(request)
    return download.download(epn, file_string)


@experiment_access_required
def download_experiment(request, experiment_id, comptype=''):

    par = models.ExperimentParameter.objects.filter(parameterset__experiment=
                                                    experiment_id)
    epn = par.get(name__name='EPN').string_value
    download = VBLDownload(request)
    return download.download(epn, '')
