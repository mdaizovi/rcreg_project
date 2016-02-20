#con_event.urls

from django.conf.urls import patterns, include, url
from con_event import views
from con_event.models import Country, State, Con, Registrant
from django.views.generic import TemplateView



urlpatterns = patterns('',

    url(r'^profile/', 'con_event.views.registrant_profile',name='registrant_profile'),
    url(r'^announcements/', 'con_event.views.all_announcements',name='all_announcements'),
    url(r'^announcement/(?P<slugname>\w+)/$', 'con_event.views.announcement',name='announcement'),
#write url for each individual annoucement using slugname


    # url(r'^all/$', 'con_event.views.sessions', name='sessions'),
    # url(r'^get/(?P<session_id>\d+)/$', 'con_event.views.session', name='get_session'),

)
