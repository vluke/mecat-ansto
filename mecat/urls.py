from django.conf.urls.defaults import patterns
from django.conf import settings
from django.contrib import admin
from django.shortcuts import Http404
admin.autodiscover()


def no_view(request):
    raise Http404


urlpatterns = patterns('',
                       (r'^$', 'tardis.tardis_portal.views.experiment_index'),
                       (r'^vbl/experiment/register/$', 'mecat.register.register_metaman'),
                       (r'^vbl/download/datafile/(?P<datafile_id>\d+)/$', 'mecat.download.download_datafile'),
                       (r'^vbl/download/experiment/(?P<experiment_id>\d+)/(?P<comptype>[a-z]{3})/$', 'mecat.download.download_experiment'),
                       (r'^vbl/download/datafiles/$', 'mecat.download.download_datafiles'),
                       (r'^rif_cs/', no_view),
                       (r'^accounts/manage_auth_methods/', no_view),
                       (r'^accounts/register/', no_view),
		       (r'^create/$', no_view),
                       (r'^ajax/upload_complete/$', no_view),
                       (r'^ajax/upload_files/', no_view),
                       (r'^ansto_media/(?P<path>.*)$', 'django.views.static.serve',
                        {'document_root': settings.ANSTO_MEDIA_ROOT}),
                       )

from tardis.urls import urlpatterns as tardisurls
urlpatterns += tardisurls
