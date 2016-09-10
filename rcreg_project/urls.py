from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'con_event.views.index', name='index'),
    url(r'^WTFAQ/', 'con_event.views.WTFAQ', name='WTFAQ'),
    url(r'^CheapAir/', TemplateView.as_view(
        template_name='CheapAirWidgetEdited.html'),
        name='CheapAir'),
    url(r'^CheapAirDynamic/', 'con_event.views.CheapAirDynamic',
        name='CheapAirDynamic'),
    url(r'^con/', include('con_event.urls')),
    url(r'^scheduler/', include('scheduler.urls')),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^', include('swingtime.urls')),  # Avoid ugly swingtime prefix
    # make sure to not use 'calendar' or 'events' elsewhere,
    # else will conflict with swingtime urls.

    # questionnaire urls
    # url(r'q/', include('questionnaire.urls')),
    #
    # url(r'^take/(?P<questionnaire_id>[0-9]+)/$', 'questionnaire.views.generate_run'),
    # url(r'^$', 'questionnaire.page.views.page', {'page_to_render' : 'index'}),
    # url(r'^(?P<lang>..)/(?P<page_to_trans>.*)\.html$', 'questionnaire.page.views.langpage'),
    # url(r'^(?P<page_to_render>.*)\.html$', 'questionnaire.page.views.page'),
    # url(r'^setlang/$', 'questionnaire.views.set_language'),

    ]
