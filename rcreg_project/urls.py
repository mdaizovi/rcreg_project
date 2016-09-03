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
    ]
