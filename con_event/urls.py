from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from con_event import views
from con_event.models import Country, State, Con, Registrant


urlpatterns = patterns('',
    url(r'^profile/',
            'con_event.views.registrant_profile',
            name='registrant_profile'
            ),
    url(r'^announcements/',
            'con_event.views.all_announcements',
            name='all_announcements'
            ),
    url(r'^announcement/(?P<slugname>\w+)/$',
            'con_event.views.announcement',
            name='announcement'
            ),
    url(r'^know_thyself(?:/(?P<con_id>\d+))?/$',
            'con_event.views.know_thyself',
            name='know_thyself'
            ),
    url(r'^upload/registrants/',
            'con_event.views.upload_reg',
            name='upload_reg'
            ),
    )
