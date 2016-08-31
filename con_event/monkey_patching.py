#reference: http://stackoverflow.com/questions/2939941/django-user-model-adding-function
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME
from django.db.models import Q


"""This whole file is methods I've added to the User class.
I know that monkey patching is frowned upon,
but these methods are peppered all over the views, templates, etc, so changing them is ill-advised.
Sometimes models are imported in method to avoid import error."""


def is_a_boss(self):
    #if self in list(User.objects.filter(Q(is_staff=True)|Q(groups__name__in=[BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME]))):
    #raising the bar for what it means to be a boss, commenting for now to see if that causes problems.
    if self in list(User.objects.filter(Q(is_superuser=True)|Q(groups__name__in=[BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME]))):
        return True
    else:
        return False

def is_the_boss(self):
    #Checks to see if user is a superuser, or in khaleesi group
    if self in list(User.objects.filter(Q(is_superuser=True)|Q(groups__name__in=[BIG_BOSS_GROUP_NAME]))):
        return True
    else:
        return False

def is_a_coach(self):
    if hasattr(self, 'coach'):
        from scheduler.models import Coach
        coach=Coach.objects.get(user=self)
        return coach
    else:
        return False

def is_a_coach_this_con(self,con):
    coach=self.is_a_coach()
    if coach:
        from scheduler.models import Training
        this_con_trainings=list(Training.objects.filter(coach=coach, con=con))
        if len(this_con_trainings)>0:
            return this_con_trainings
        else:
            return None
    else:
        return None


def can_edit_score(self):
    if self in list(User.objects.filter(groups__name__in=["NSO",BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME])):
        return True
    else:
        return False

def registrants(self):
    from con_event.models import Registrant

    try:
        registrant_list= list(self.registrant_set.all())
    except:
        registrant_list=None

    return registrant_list

def trainings_coached(self):
    coach=self.is_a_coach()
    if coach:
        return coach.training_set.all()
    else:
        return None

def all_cons(self):
    from con_event.models import Con
    conlist=[]
    all_reg= self.registrants()
    if all_reg:
        for reg in all_reg:
            conlist.append(reg.con)

    if len(conlist)>0:
        return conlist
    else:
        if self.is_the_boss():#RollerTron has no registrants
            return list(Con.objects.all())
        else:
            return None


def upcoming_registrants(self):
    """gets user's registrants that are assosciated w/ any cons that have not occurred yet."""
    from con_event.models import Registrant,Con

    cons=Con.objects.upcoming_cons()
    reglist=list(Registrant.objects.filter(user=self, con__in=cons))
    if len(reglist)>0:
        return reglist
    else:
        return None

def upcoming_cons(self):
    conlist=[]
    upcoming_reg= self.upcoming_registrants()
    if upcoming_reg:
        for reg in upcoming_reg:
            conlist.append(reg.con)
        if len(conlist)>0:
            return conlist
        else:
            return None
    else:
        return None

def get_most_recent_registrant(self):

    from con_event.models import Registrant

    most_recent_user=None
    reglist=list(Registrant.objects.filter(user=self).order_by("-con"))
    if len(reglist)>0:
        most_recent_user=reglist[0]
    return most_recent_user

def get_registrant_for_most_upcoming_con(self):
    from con_event.models import Registrant,Con

    con=Con.objects.most_upcoming()
    try:
        relevant_user=Registrant.objects.get(user=self, con=con)
    except:
        relevant_user=None
    return relevant_user

def get_my_schedule_url(self):
    """Used for bosses to check coach's schedule"""
    from scheduler.views import my_schedule
    url = "%s?user=%s" % (reverse('scheduler.views.my_schedule'),self.pk)
    return url

User.add_to_class("is_a_boss",is_a_boss)
User.add_to_class("is_the_boss",is_the_boss)
User.add_to_class("is_a_coach",is_a_coach)
User.add_to_class("is_a_coach_this_con",is_a_coach_this_con)
User.add_to_class("can_edit_score",can_edit_score)
User.add_to_class("registrants",registrants)
User.add_to_class('all_cons',all_cons)
User.add_to_class('upcoming_cons',upcoming_cons)
User.add_to_class("trainings_coached",trainings_coached)
User.add_to_class("upcoming_registrants",upcoming_registrants)
User.add_to_class("get_most_recent_registrant",get_most_recent_registrant)
User.add_to_class("get_registrant_for_most_upcoming_con",get_registrant_for_most_upcoming_con)
User.add_to_class("get_my_schedule_url",get_my_schedule_url)
