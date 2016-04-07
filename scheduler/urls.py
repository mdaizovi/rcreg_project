#scheduler.urls

from django.conf.urls import patterns, include, url
from scheduler import views
from scheduler.models import Challenge, Training
from django.views.generic import TemplateView



urlpatterns = patterns('',
    url(r'^challenges/con/(?P<con_id>\d+)/$', 'scheduler.views.challenges_home',name='challenges_home_con'),
    url(r'^challenges/$', 'scheduler.views.challenges_home',name='challenges_home'),
    url(r'^my_challenges/', 'scheduler.views.my_challenges',name='my_challenges'),
    #url(r'^propose_new_challenge_new_team/', 'scheduler.views.propose_new_challenge_new_team',name='propose_new_challenge_new_team'),
    url(r'^propose_new_challenge/', 'scheduler.views.propose_new_challenge',name='propose_new_challenge'),
    #url(r'^propose_new_game_new_team/', 'scheduler.views.propose_new_game_new_team',name='propose_new_game_new_team'),
    url(r'^propose_new_game/', 'scheduler.views.propose_new_game',name='propose_new_game'),
    url(r'^captain/email/(?P<roster_id>\d+)/$', 'scheduler.views.email_captain', name='email_captain'),

    # this can be training or challenge roster? or do i need all new action?
    url(r'^roster/edit/(?P<roster_id>\d+)/$', 'scheduler.views.edit_roster', name='edit_roster'),

    url(r'^challenge/view/(?P<activity_id>\d+)/$', 'scheduler.views.view_challenge', name='view_challenge'),
    url(r'^challenge/edit/(?P<activity_id>\d+)/$', 'scheduler.views.edit_challenge', name='edit_challenge'),
    url(r'^challenge/respond/', 'scheduler.views.challenge_respond', name='challenge_respond'),
    url(r'^challenge/submit/', 'scheduler.views.challenge_submit', name='challenge_submit'),

    url(r'^trainings/con/(?P<con_id>\d+)/$', 'scheduler.views.trainings_home',name='trainings_home_con'),
    url(r'^trainings/$', 'scheduler.views.trainings_home',name='trainings_home'),


    url(r'^my_trainings/', 'scheduler.views.my_trainings',name='my_trainings'),
    url(r'^propose_new_training/', 'scheduler.views.propose_new_training',name='propose_new_training'),
    #add this later with logic about if near training time or not, can see reg/audit rosters.
    url(r'^training/view/(?P<activity_id>\d+)/$', 'scheduler.views.view_training', name='view_training'),
    url(r'^training/edit/(?P<activity_id>\d+)/$', 'scheduler.views.edit_training', name='edit_training'),
    url(r'^training/register/(?P<activity_id>\d+)/$', 'scheduler.views.register_training', name='register_training'),

    url(r'^coach/view/(?P<coach_id>\d+)/$', 'scheduler.views.view_coach', name='view_coach'),
    url(r'^coach/email/(?P<coach_id>\d+)/$', 'scheduler.views.email_coach', name='email_coach'),
    url(r'^coach/profile/', 'scheduler.views.coach_profile',name='coach_profile'),

)
