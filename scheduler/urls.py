from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from scheduler import views
from scheduler.models import Challenge, Training


urlpatterns = patterns('',
#-------------------------------------------------------------------------------
    #  Challenge-related urls
    url(r'^challenges/con/(?P<con_id>\d+)/$',
            'scheduler.views.challenges_home',
            name='challenges_home_con'
            ),
    url(r'^challenges/$',
            'scheduler.views.challenges_home',
            name='challenges_home'
            ),
    url(r'^my_challenges/',
            'scheduler.views.my_challenges',
            name='my_challenges'
            ),
    url(r'^propose_new_challenge/',
            'scheduler.views.propose_new_challenge',
            name='propose_new_challenge'
            ),
    url(r'^captain/email/(?P<roster_id>\d+)/$',
            'scheduler.views.email_captain',
            name='email_captain'
            ),
    url(r'^challenge/view/(?P<activity_id>\d+)/$',
            'scheduler.views.view_challenge',
            name='view_challenge'
            ),
    url(r'^challenge/edit/(?P<activity_id>\d+)/$',
            'scheduler.views.edit_challenge',
            name='edit_challenge'
            ),
    url(r'^challenge/respond/',
            'scheduler.views.challenge_respond',
            name='challenge_respond'
            ),
    url(r'^challenge/submit/',
            'scheduler.views.challenge_submit',
            name='challenge_submit'
            ),
#-------------------------------------------------------------------------------
    #  Roster-related url
    url(r'^roster/edit/(?P<roster_id>\d+)/$',
            'scheduler.views.edit_roster',
            name='edit_roster'
            ),
#-------------------------------------------------------------------------------
    #  Training-related urls
    url(r'^trainings/con/(?P<con_id>\d+)/$',
            'scheduler.views.trainings_home',
            name='trainings_home_con'
            ),
    url(r'^trainings/$',
            'scheduler.views.trainings_home',
            name='trainings_home'
            ),
    url(r'^my_trainings/',
            'scheduler.views.my_trainings',
            name='my_trainings'
            ),
    url(r'^propose_new_training/',
            'scheduler.views.propose_new_training',
            name='propose_new_training'
            ),
    #  regex below so that Occurrence ID can be included or omitted.
    url(r'^training/view/(?P<activity_id>\d+)(?:/(?P<o_id>\d+))?/$',
            'scheduler.views.view_training',
            name='view_training'
            ),
    url(r'^training/edit/(?P<activity_id>\d+)/$',
            'scheduler.views.edit_training',
            name='edit_training'
            ),
    url(r'^training/register/(?P<o_id>\d+)/$',
            'scheduler.views.register_training',
            name='register_training'
            ),
    url(r'^coach/view/(?P<coach_id>\d+)/$',
            'scheduler.views.view_coach',
            name='view_coach'
            ),
    url(r'^coach/email/(?P<coach_id>\d+)/$',
            'scheduler.views.email_coach',
            name='email_coach'
            ),
    url(r'^coach/profile/',
            'scheduler.views.coach_profile',
            name='coach_profile'
            ),
#-------------------------------------------------------------------------------
    #  Both Challenge and Training, or Neutral
    url(r'^my_schedule/',
            'scheduler.views.my_schedule',
            name='my_schedule'
            ),
)
