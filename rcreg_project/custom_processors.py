#custom_processors.py
from rcreg_project.settings import CUSTOM_SITE_ADMIN_EMAIL, RC_GENERAL_ADMIN_EMAIL
#from django.conf import settings#this is for time zone?

# def unaccepted_challenge_notifications(request):
#     user=request.user
#     NOTIFY_UNACCEPTED_CHALLENGES=None
#     if user.is_authenticated():
#         try:
#             registrant_upcoming_con=user.get_registrant_for_most_upcoming_con()
#             NOTIFY_UNACCEPTED_CHALLENGES=len(list(registrant_upcoming_con.unaccepted_challenges()))
#         except:
#             NOTIFY_UNACCEPTED_CHALLENGES=None
#     return {'NOTIFY_UNACCEPTED_CHALLENGES': NOTIFY_UNACCEPTED_CHALLENGES}
#
# def pending_challenge_notifications(request):
#     from django.conf import settings#this is for time zone?
#     user=request.user
#     NOTIFY_PENDING_CHALLENGES=None
#     if user.is_authenticated():
#         try:
#             registrant_upcoming_con=user.get_registrant_for_most_upcoming_con()
#             con=registrant_upcoming_con.con
#             if con.can_submit_chlg():
#                 NOTIFY_PENDING_CHALLENGES=len(registrant_upcoming_con.unsubmitted_challenges())
#         except:
#             NOTIFY_PENDING_CHALLENGES=None
#     return {'NOTIFY_PENDING_CHALLENGES': NOTIFY_PENDING_CHALLENGES}


def all_challenge_notifications(request):
    from django.conf import settings#this is for time zone?
    user=request.user
    NOTIFY_PENDING_CHALLENGES=None
    NOTIFY_UNACCEPTED_CHALLENGES=None
    ALL_CHALLENGE_NOTIFY=0
    if user.is_authenticated():
        try:
            registrant_upcoming_con=user.get_registrant_for_most_upcoming_con()
            NOTIFY_UNACCEPTED_CHALLENGES=len(list(registrant_upcoming_con.unaccepted_challenges()))
            con=registrant_upcoming_con.con
            if con.can_submit_chlg():
                NOTIFY_PENDING_CHALLENGES=len(registrant_upcoming_con.unsubmitted_challenges())
        except:
            pass
    if NOTIFY_PENDING_CHALLENGES:
        ALL_CHALLENGE_NOTIFY+=NOTIFY_PENDING_CHALLENGES
    if NOTIFY_UNACCEPTED_CHALLENGES:
        ALL_CHALLENGE_NOTIFY+=NOTIFY_UNACCEPTED_CHALLENGES
    if ALL_CHALLENGE_NOTIFY<=0:
        ALL_CHALLENGE_NOTIFY=None

    return {'NOTIFY_PENDING_CHALLENGES': NOTIFY_PENDING_CHALLENGES,'NOTIFY_UNACCEPTED_CHALLENGES':NOTIFY_UNACCEPTED_CHALLENGES,'ALL_CHALLENGE_NOTIFY':ALL_CHALLENGE_NOTIFY}


def get_rc_admin_email(request):
    return {'RC_GENERAL_ADMIN_EMAIL':RC_GENERAL_ADMIN_EMAIL}

def get_site_admin_email(request):
    return {'CUSTOM_SITE_ADMIN_EMAIL':CUSTOM_SITE_ADMIN_EMAIL}
