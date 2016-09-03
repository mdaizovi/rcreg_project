from django.db.models import Q
from rcreg_project.settings import (CUSTOM_SITE_ADMIN_EMAIL,
    RC_GENERAL_ADMIN_EMAIL)


def all_challenge_notifications(request):
    """User notified via sidebar if:
    User has unaccepted or unsubmitted challenges, or
    submission window is closed due to too many challenges captained by User.
    """
    from django.conf import settings  # avoid circular import
    from scheduler.models import Challenge  # avoid circular import
    user = request.user
    NOTIFY_PENDING_CHALLENGES = None
    NOTIFY_UNACCEPTED_CHALLENGES = None
    ALL_CHALLENGE_NOTIFY = 0

    if user.is_authenticated():
        try:
            registrant_upcoming_con = (
                user.get_registrant_for_most_upcoming_con())
            if not Challenge.objects.submission_full(
                    registrant_upcoming_con.con):

                con = registrant_upcoming_con.con
                if con.can_submit_chlg():
                    my_rosters = list(Roster.objects.filter(
                                    captain=registrant_upcoming_con))

                    NOTIFY_PENDING_CHALLENGES = len(list(
                        Challenge.objects.filter(Q(roster1__in=my_rosters) |
                        Q(roster2__in=my_rosters)).filter(submitted_on=None)))

                NOTIFY_UNACCEPTED_CHALLENGES = len(list(
                    Challenge.objects.filter(Q(
                    roster1__captain=registrant_upcoming_con) |
                    Q(roster2__captain=registrant_upcoming_con)).
                    filter(Q(captain1accepted=False) |
                    Q(captain2accepted=False))))

        except:
            pass

    if NOTIFY_PENDING_CHALLENGES:
        ALL_CHALLENGE_NOTIFY += NOTIFY_PENDING_CHALLENGES
    if NOTIFY_UNACCEPTED_CHALLENGES:
        ALL_CHALLENGE_NOTIFY += NOTIFY_UNACCEPTED_CHALLENGES
    if ALL_CHALLENGE_NOTIFY <= 0:
        ALL_CHALLENGE_NOTIFY = None

    return {'NOTIFY_PENDING_CHALLENGES': NOTIFY_PENDING_CHALLENGES,
            'NOTIFY_UNACCEPTED_CHALLENGES': NOTIFY_UNACCEPTED_CHALLENGES,
            'ALL_CHALLENGE_NOTIFY': ALL_CHALLENGE_NOTIFY
            }


def get_rc_admin_email(request):
    """Gets RC_GENERAL_ADMIN_EMAIL from settings, used in templates."""

    return {'RC_GENERAL_ADMIN_EMAIL': RC_GENERAL_ADMIN_EMAIL}


def get_site_admin_email(request):
    """Gets CUSTOM_SITE_ADMIN_EMAIL from settings, used in templates."""

    return {'CUSTOM_SITE_ADMIN_EMAIL': CUSTOM_SITE_ADMIN_EMAIL}


def get_upcoming_con_context(request):
    from con_event.models import Con  # avoid circular import
    upcoming_con_context = Con.objects.most_upcoming()

    return {'up_con_year': upcoming_con_context.start.year,
            'up_con_month': upcoming_con_context.start.month
            }


def upcoming_days(request):
    # I have no idea where I use this.
    # Maybe I intended to and forgot of maybe it's buried somewhere.
    # Maybe it's used in the swingtime/calendar?
    from con_event.models import Con  # avoid circular import
    upcoming = Con.objects.most_upcoming()
    upcoming_days = upcoming.get_date_range()

    return {'upcoming_days': upcoming_days}
