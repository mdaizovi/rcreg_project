from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q

from rcreg_project.settings import BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME


"""This whole file is methods I've added to the User class.
I know that monkey patching is frowned upon, but I thought it the lesser of 2
evils, between monkey patching and using a custom User model.
These methods are peppered all over the views, templates, etc,
so changing them is ill-advised.
Sometimes models are imported in method to avoid circular import.
"""


def is_a_boss(self):
    """Checks to see if user is either a superuser,
    or in 1 of the 2 custom boss groups.
    Just being staff isn't good enough.
    """

    if self in list(User.objects.filter(
                    Q(is_superuser=True) |
                    Q(groups__name__in=[
                            BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME
                            ]))):
        return True
    else:
        return False


def is_the_boss(self):
    """Checks to see if user is either a superuser,
    or in the main boss.
    Just being staff or secondary boss isn't good enough.
    """

    if self in list(User.objects.filter(
                    Q(is_superuser=True) | Q(groups__name__in=[
                                             BIG_BOSS_GROUP_NAME
                                             ])
                    )):
        return True
    else:
        return False


def is_a_coach(self):
    """Returns True if user is associated with a coach object."""

    if hasattr(self, 'coach'):

        from scheduler.models import Coach  # Avoid circular import
        coach = Coach.objects.get(user=self)
        return coach

    else:
        return False


def is_a_coach_this_con(self, con):
    """Extend is_a_coach to return True iff they are a coach for con supplied.
    Having been a coach ever, for a different con, is not good enough.
    """

    coach = self.is_a_coach()

    if coach:

        from scheduler.models import Training  # Avoid circular import

        this_con_trains = list(Training.objects.filter(coach=coach, con=con))

        if len(this_con_trains) > 0:
            return this_con_trains
        else:
            return None
    else:
        return None


def can_edit_score(self):
    """Return True if user is in NSO group or either of 2 custom boss groups.
    Also used to grant other privileges, like see and edit communication box"""

    editor_group_names = ["NSO", BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME]
    sceditors = list(User.objects.filter(groups__name__in=editor_group_names))

    if self in sceditors:
        return True
    else:
        return False


def registrants(self):
    """Returns list of registrants associated w/user, or None"""

    from con_event.models import Registrant  # Avoid circular import
    registrant_list = list(self.registrant_set.all()) or None

    return registrant_list


def trainings_coached(self):
    """If user is a coach, returns training set associated w/ coach.
    Else, returns None.
    """

    coach = self.is_a_coach()

    if coach:
        return coach.training_set.all()
    else:
        return None


def all_cons(self):
    """Returns list of all cons user has a registrant for.
    If has no cons but is a superuser, like RollerTron,
    returns list of all cons.
    """

    from con_event.models import Con  # Avoid circular import
    conlist = []
    all_reg = self.registrants()

    if all_reg:
        for reg in all_reg:
            conlist.append(reg.con)
    elif self.is_the_boss():
        # Superuser RollerTron has no Registrants,
        # but is still associated with all Cons.
        conlist = list(Con.objects.all())

    if len(conlist) > 0:
        return conlist

    else:
        return None


def upcoming_registrants(self):
    """If user associated w/registrants that are associated w/ an upcoming con,
    returns list of registrants. If no registrants, or all registrant cons
    have aready occurred, returns None
    """

    from con_event.models import Registrant, Con  # Avoid circular import

    cons = Con.objects.upcoming_cons()
    reglist = list(Registrant.objects.filter(user=self, con__in=cons)) or None

    return reglist


def upcoming_cons(self):
    """Upcoming cons associated w/ user.
    Like upcoming_registrants, but only returns list of cons, or None.
    """

    conlist = []
    upcoming_reg = self.upcoming_registrants()

    if upcoming_reg:
        for reg in upcoming_reg:
            conlist.append(reg.con)

        if len(conlist) > 0:
            return conlist
        else:
            return None

    else:
        return None


def get_most_recent_registrant(self):
    """If user has a registrant, returns most recent one, even if past.
    Otherwise, if no registrants, returns None.
    """

    from con_event.models import Registrant  # Avoid circular import

    reglist = (
        list(Registrant.objects.filter(user=self).order_by("-con")) or None)

    if reglist:
        most_recent_reg = reglist[0]
    else:
        most_recent_reg = None

    return most_recent_reg


def get_registrant_for_most_upcoming_con(self):
    """If user has a registrant for most upcoming con, returns it.
    Else, returns None.
    """

    from con_event.models import Registrant, Con  # Avoid circular import

    con = Con.objects.most_upcoming()
    relevant_user = Registrant.objects.get(user=self, con=con) or None

    return relevant_user


def get_my_schedule_url(self):
    """Used for bosses to check coach's schedule.
    Otherwise registrants can check only own schedule,
    don't need to provide user pk.
    """

    from scheduler.views import my_schedule  # Avoid circular import

    url = "%s?user=%s" % (reverse('scheduler.views.my_schedule'), self.pk)

    return url


User.add_to_class("is_a_boss", is_a_boss)
User.add_to_class("is_the_boss", is_the_boss)
User.add_to_class("is_a_coach", is_a_coach)
User.add_to_class("is_a_coach_this_con", is_a_coach_this_con)
User.add_to_class("can_edit_score", can_edit_score)
User.add_to_class("registrants", registrants)
User.add_to_class("all_cons", all_cons)
User.add_to_class("upcoming_cons", upcoming_cons)
User.add_to_class("trainings_coached", trainings_coached)
User.add_to_class("upcoming_registrants", upcoming_registrants)
User.add_to_class("get_most_recent_registrant", get_most_recent_registrant)
User.add_to_class(
    "get_registrant_for_most_upcoming_con",
    get_registrant_for_most_upcoming_con)
User.add_to_class("get_my_schedule_url", get_my_schedule_url)
