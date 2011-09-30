# views and embargohandler

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

from tardis.tardis_portal.models import Experiment
from tardis.tardis_portal.auth import auth_service
from tardis.tardis_portal.auth.localdb_auth import django_user, django_group

from mecat.vbl_auth import auth_key as vbl_auth_key
from mecat.forms import RegisterMetamanForm

from django import forms
from django.db.models import Q


logger = logging.getLogger('tardis.mecat')


class EmbargoHandler(object):
    def __init__(self, experiment_id):
        self.experiment_id = experiment_id


class EmbargoSearchForm(forms.Form):
    from django.forms.extras.widgets import SelectDateWidget
    start_date = forms.DateField(required=False, widget=SelectDateWidget())
    end_date = forms.DateField(required=False, widget=SelectDateWidget())
    title = forms.CharField(required=False)
    proposal_id = forms.IntegerField(required=False)
    author = forms.CharField(required=False)


# TODO Permission check
def index(request):
    c = Context({'form': EmbargoSearchForm(),
                 'subtitle': 'Embargo Periods',
                 'searched': False,
                 'header': 'Register Metaman File'})
    return render_to_response('tardis_portal/embargo_index.html', c)


# TODO Permission check
def search(request):
    form = EmbargoSearchForm(request.GET)
    if form.is_valid():
        search_results = _search(form.cleaned_data)
        annotated_search_results = [{
            'title': e.title,
            'authors': ', '.join([a.author for a in e.author_experiment_set.all()]),
            'start_time': e.start_time,
            'end_time': e.end_time,
            'expiry': _get_formatted_expiry(e),
            } for e in search_results]
    else:
        annotated_search_results = []

    c = Context({'form': form,
                 'subtitle': 'Embargo Periods',
                 'searched': form.is_valid(),
                 'search_results': annotated_search_results,
                 'header': 'Register Metaman File'})
    return render_to_response('tardis_portal/embargo_index.html', c)


def _get_formatted_expiry(experiment):
    return None  # TODO


def _search(cleaned_data):
    query = Q()  # no filter
    start_date = cleaned_data.get('start_date')
    end_date = cleaned_data.get('end_date')
    title = cleaned_data.get('title')
    proposal_id = cleaned_data.get('proposal_id')
    author = cleaned_data.get('author')

    if start_date:
        query &= Q(start_time__gte=start_date)
    if end_date:
        query &= Q(end_time__lte=end_date)
    if title:
        query &= Q(title__icontains=title)
    if author:
        query &= Q(author_experiment__author__icontains=author)
    if proposal_id:
        query &= Q(experimentparameterset__experimentparameter__name__name='EPN', experimentparameterset__experimentparameter__string_value__contains=proposal_id)

    return Experiment.objects.filter(query)
