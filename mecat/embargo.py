# views and embargohandler

import logging

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.template import Context
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from tardis.tardis_portal.models import Experiment, ExperimentParameterSet, ParameterName, Schema, ExperimentParameter
from tardis.tardis_portal.shortcuts import render_response_index

logger = logging.getLogger('tardis.mecat')

EXPIRY_DATE_KEY = 'expiry'
NEVER_EXPIRE_KEY = 'never_expire'
NAMESPACE = "http://www.tardis.edu.au/schemas/ansto_embargo/2011/06/10"


class EmbargoHandler(object):

    def __init__(self, experiment_id, create=False):
        self.experiment = Experiment.objects.get(pk=experiment_id)

        parametersets = ExperimentParameterSet.objects.filter(
            schema__namespace=NAMESPACE, experiment__id=experiment_id)

        self.schema, _ = Schema.objects.get_or_create(namespace=NAMESPACE, name='Embargo Details')
        self.expiry_date, _ = ParameterName.objects.get_or_create(schema=self.schema, name=EXPIRY_DATE_KEY, full_name='Expiry', immutable=True, data_type=ParameterName.DATETIME)
        self.never_expire, _ = ParameterName.objects.get_or_create(schema=self.schema, name=NEVER_EXPIRE_KEY, full_name='Never Expires', immutable=True, data_type=ParameterName.STRING)

        if len(parametersets) == 1:
            self.parameterset = parametersets[0]
        elif create:
            self.parameterset = ExperimentParameterSet(experiment=self.experiment, schema=self.schema)
            self.parameterset.save()
        else:
            self.parameterset = None

    def never_expires(self):
        never_expire = self._get_or_none(NEVER_EXPIRE_KEY)
        if never_expire:
            return True
        expiry_date = self._get_or_none(EXPIRY_DATE_KEY)
        if expiry_date:
            return False
        else:
            return self.experiment.end_time == None

    def has_any_expiry(self):
        return not self.never_expires()

    def can_be_defaulted(self):
        expiry_date = self._get_or_none(EXPIRY_DATE_KEY)
        never_expires = self._get_or_none(NEVER_EXPIRE_KEY)
        return never_expires or expiry_date

    def because_no_end_date(self):
        if self._get_or_none(NEVER_EXPIRE_KEY):
            return False
        return self.experiment.end_time == None

    def get_expiry_date(self):
        ''' returns calculated or explicit expiry or None '''
        import datetime
        if self.never_expires():
            return None

        explicit_expiry = self._get_or_none(EXPIRY_DATE_KEY)
        if explicit_expiry:
            return explicit_expiry.datetime_value
        else:
            return self.experiment.end_time + datetime.timedelta(settings.EMBARGO_DAYS)

    def _get_or_none(self, name):
        if not self.parameterset:
            return None
        params = self.parameterset.experimentparameter_set.filter(name__name=name)
        if params.count() == 0:
            return None
        else:
            return params[0]

    def prevent_expiry(self):
        if not self.parameterset:
            raise Exception('incorrectly initialised, call with create=True')
        params = self.parameterset.experimentparameter_set
        params.all().delete()
        param = ExperimentParameter(name=self.never_expire, string_value='True', parameterset=self.parameterset)
        param.save()

        self.experiment.public = False
        self.experiment.save()

    def reset_to_default(self):
        import datetime
        if self.parameterset:
            self.parameterset.delete()

            expiry_date = self.get_expiry_date()
            if expiry_date and expiry_date.date() < datetime.date.today():
                self.experiment.public = True
            else:
                self.experiment.public = False
            self.experiment.save()

        else:
            logger.warn('tried to delete parameterset that does not exist')

    def set_expiry(self, date_string):
        if not self.parameterset:
            raise Exception('incorrectly initialised, call with create=True')

        params = self.parameterset.experimentparameter_set
        params.all().delete()
        import datetime
        expiry_date = datetime.datetime.strptime(date_string, '%Y/%m/%d')
        param = ExperimentParameter(name=self.expiry_date, datetime_value=expiry_date, parameterset=self.parameterset)
        param.save()

        if expiry_date.date() < datetime.date.today():
            self.experiment.public = True
        else:
            self.experiment.public = False
        self.experiment.save()

class EmbargoSearchForm(forms.Form):
    start_date = forms.DateField(required=False, input_formats=['%d/%m/%Y'], widget=forms.DateInput(format='%d/%m/%Y', attrs={"class": "date_input"}))
    end_date = forms.DateField(required=False, input_formats=['%d/%m/%Y'], widget=forms.DateInput(format='%d/%m/%Y', attrs={"class": "date_input"}))
    title = forms.CharField(required=False)
    proposal_id = forms.IntegerField(required=False)
    author = forms.CharField(required=False)
    include_public = forms.BooleanField(required=False)


@permission_required('tardis_portal.embargo_admin')
def index(request):
    c = Context({'form': EmbargoSearchForm(),
                 'subtitle': 'Embargo Periods',
                 'searched': False,
                 'header': 'Register Metaman File'})

    return HttpResponse(render_response_index(request, 'tardis_portal/embargo_index.html', c))


def _proposal_id(experiment):
    epns = ExperimentParameter.objects.filter(name__name='EPN', parameterset__experiment=experiment)
    if epns.count() > 0:
        return epns[0].string_value
    
    
@never_cache
@permission_required('tardis_portal.embargo_admin')
def search(request):
    form = EmbargoSearchForm(request.GET)
    if form.is_valid():
        search_results = _search(form.cleaned_data)
        annotated_search_results = [{
            'title': e.title,
            'authors': ', '.join([a.author for a in e.author_experiment_set.all()]),
            'start_time': e.start_time,
            'end_time': e.end_time,
            'url': e.get_absolute_url(),
            'public': e.public,
            'proposal_id': _proposal_id(e),
            'id': e.id,
            } for e in search_results]
    else:
        annotated_search_results = []

    c = Context({'form': form,
                 'subtitle': 'Embargo Periods',
                 'searched': form.is_valid(),
                 'search_results': annotated_search_results,
                 'header': 'Register Metaman File'})
    return HttpResponse(render_response_index(request,
                        'tardis_portal/embargo_index.html', c))


@require_POST
@permission_required('tardis_portal.embargo_admin')
def default_expiry(request, experiment_id):
    embargo_handler = EmbargoHandler(experiment_id)
    embargo_handler.reset_to_default()
    return HttpResponse('{"success": true}', mimetype='application/json')


@require_POST
@permission_required('tardis_portal.embargo_admin')
def prevent_expiry(request, experiment_id):
    embargo_handler = EmbargoHandler(experiment_id, create=True)
    embargo_handler.prevent_expiry()
    return HttpResponse('{"success": true}', mimetype='application/json')


@require_POST
@permission_required('tardis_portal.embargo_admin')
def set_expiry(request, experiment_id):
    embargo_handler = EmbargoHandler(experiment_id, create=True)
    embargo_handler.set_expiry(request.POST['date'])
    return HttpResponse('{"success": true}', mimetype='application/json')


def _search(cleaned_data):
    query = Q()

    start_date = cleaned_data.get('start_date')
    end_date = cleaned_data.get('end_date')
    title = cleaned_data.get('title')
    proposal_id = cleaned_data.get('proposal_id')
    author = cleaned_data.get('author')
    include_public = cleaned_data.get('include_public')

    if not include_public:
        query &= Q(public=False)
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
