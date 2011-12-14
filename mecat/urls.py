from django.conf.urls.defaults import patterns, include
from django.conf import settings
from django.contrib import admin
from django.shortcuts import Http404
admin.autodiscover()


def no_view(request, *args, **kwargs):
    raise Http404

embargo_urls = patterns('mecat.embargo',
                        (r'^$', 'index'),
                        (r'^search/$', 'search'),
                        (r'^default_expiry/(?P<experiment_id>\d+)/$', 'default_expiry'),
                        (r'^prevent_expiry/(?P<experiment_id>\d+)/$', 'prevent_expiry'),
                        (r'^set_expiry/(?P<experiment_id>\d+)/$', 'set_expiry'),
                        )


urlpatterns = patterns('',
                       (r'^$', 'tardis.tardis_portal.views.experiment_index'),
                       (r'^vbl/experiment/register/$', 'mecat.register.register_metaman'),
                       (r'^vbl/download/datafile/(?P<datafile_id>\d+)/$', 'mecat.download.download_datafile'),
                       (r'^vbl/download/experiment/(?P<experiment_id>\d+)/(?P<comptype>[a-z]{3})/$', 'mecat.download.download_experiment'),
                       (r'^vbl/download/datafiles/$', 'mecat.download.download_datafiles'),
                       (r'^rif_cs/', no_view),
                       (r'^accounts/manage_auth_methods/', no_view),
                       (r'^accounts/register/', no_view),
                       (r'^experiment/create/$', no_view),
                       (r'^experiment/view/(?P<experiment_id>\d+)/publish/', no_view),
                       (r'^ansto_media/(?P<path>.*)$', 'django.views.static.serve',
                        {'document_root': settings.ANSTO_MEDIA_ROOT}),
                       (r'^embargo/', include(embargo_urls)),
                       )

from tardis.urls import urlpatterns as tardisurls
urlpatterns += tardisurls
