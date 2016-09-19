import calendar
from collections import OrderedDict
from datetime import datetime, timedelta, time
from dateutil.parser import parse
from dateutil import parser
import itertools
import logging
from random import randint, choice

from django import http
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db import connection as dbconnection
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, render, redirect,HttpResponseRedirect, render_to_response
from django.template.context import RequestContext

from swingtime.conf import settings as swingtime_settings
from con_event.forms import ConSchedStatusForm
from con_event.models import Con,Blackout,LOCATION_CATEGORY,LOCATION_TYPE,LOCATION_TYPE_FILTER,LOCATION_CATEGORY_FILTER
import django_tables2 as tables
from django_tables2  import RequestConfig
from scheduler.forms import ChalStatusForm, TrainStatusForm, CInterestForm, TInterestForm, ActCheck
from scheduler.models import Location, Training, Challenge
from scheduler.tables import ChallengeTable, TrainingTable
from swingtime import utils, forms
from swingtime.forms import DLCloneForm, SlotCreate, L1Check
from swingtime.models import Occurrence


if swingtime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(swingtime_settings.CALENDAR_FIRST_WEEKDAY)

no_list = ["", u'', None, "None"]


@login_required
def conflict_check(
    request,
    template='swingtime/conflict_check.html',
    con_id=None,
    **extra_context
):
    """Checks to see if any coaches or captains have schedule conflicts.
    Big mess of code but can check all coaches in 2 seconds and 1 db hit per coach.
    Sacrifice readability for speed. No regrets.
    """
    #start = datetime.now()

    if con_id:
        try:
            con = Con.objects.get(pk=con_id)
        except ObjectDoesNotExist:
            con = Con.objects.most_upcoming()
    else:
        con = Con.objects.most_upcoming()

    active = False
    relevant_conflicts = []
    coach_search = False
    captain_search = False
    registrant_search = False
    relevant_hard_conflicts = []
    relevant_soft_conflicts = []

    if request.method == 'POST':
        scheduled_os=list(Occurrence.objects
                .filter(start_time__gte=con.start, end_time__lte=con.end)
                .exclude(training=None,challenge=None)
                .prefetch_related('training')
                .prefetch_related('training__coach__user__registrant_set')
                .prefetch_related('challenge')
                .select_related('challenge__roster1__captain')
                .prefetch_related('challenge__roster1__participants')
                .select_related('challenge__roster2__captain')
                .prefetch_related('challenge__roster2__participants')
                )
        act_dict = {}
        busy = {}
        busy_figurehead = {}  # like busy dict, but only when reg is being a coach or captain
        all_coach_reg = []
        all_cap_reg = []
        all_participants = []

        for o in scheduled_os:
            if o.training:
                coach_reg = []
                for c in o.training.coach.all():
                    for cr in c.user.registrant_set.all():
                        if cr.con == con:
                            coach_reg.append(cr)
                            if cr not in all_coach_reg:
                                all_coach_reg.append(cr)
                            if cr not in all_participants:
                                all_participants.append(cr)

                if o.training not in act_dict:
                    act_dict[o.training] = {
                            "os": [o], "figureheads": coach_reg,
                            "participants": coach_reg
                            }
                else:
                    tmp = act_dict.get(o.training)
                    tmpo = tmp.get("os")
                    tmpo.append(o)
                    tmp["os"] = list(tmpo)

                for c in coach_reg:
                    if c not in busy:
                        busy[c] = [o]
                    else:
                        temporary = busy.get(c)
                        temporary.append(o)

                    if c not in busy_figurehead:
                        busy_figurehead[c] = [o]
                    else:
                        temporary_fig = busy_figurehead.get(c)
                        temporary_fig.append(o)

            elif o.challenge:
                if o.challenge not in act_dict:
                    figureheads = []
                    participants = []
                    for r in [o.challenge.roster1, o.challenge.roster2]:
                        figureheads.append(r.captain)
                        if r.captain not in busy:
                            busy[r.captain] = [o]
                        else:
                            temporary = busy.get(r.captain)

                        if r.captain not in busy_figurehead:
                            busy_figurehead[r.captain] = [o]
                        else:
                            temporary_fig = busy_figurehead.get(r.captain)
                            temporary_fig.append(o)

                        if r.captain not in all_cap_reg:
                            all_cap_reg.append(r.captain)

                        for p in r.participants.all():
                            participants.append(p)
                            if p not in busy:
                                busy[p] = [o]
                            else:
                                temporary = busy.get(p)
                                temporary.append(o)
                            if p not in all_participants:
                                all_participants.append(p)

                    act_dict[o.challenge] = {
                            "os": [o],
                            "figureheads": figureheads,
                            "participants": participants
                            }
                else:
                    # Should never run.
                    print "error, challenge has 2 occurrences?"

        if 'coach' in request.POST:
            coach_search = True
            active = "coach"
            relevant_reg = all_coach_reg
            # Compare busy to busy and I'll get all activity conflicts.
            # Compare busy figurehead to busy and only get times that
            # conflict w/ coaching or captaining times
            busy1 = busy_figurehead
            busy2 = busy

        elif 'captain' in request.POST:
            active = "captain"
            captain_search = True
            relevant_reg = all_cap_reg
            # Compare busy to busy and I'll get all activity conflicts.
            # Compare busy figurehead to busy and only get times that
            # conflict w/ coaching or captaining times
            busy1 = busy_figurehead
            busy2 = busy

        elif 'registrant' in request.POST:
            registrant_search = True
            active = "registrant"
            #relevant_reg=all_participants
            relevant_reg = []
            busy1 = busy
            busy2 = busy

        related_blackouts = (Blackout.objects.filter(
                registrant__in=relevant_reg)
                .prefetch_related('registrant')
                )

        for b in related_blackouts:
            r_busy = busy.get(b.registrant)
            tempo = b.make_temp_o()
            r_busy.append(tempo)
            # if b.registrant in busy_figurehead:
            #     fig_busy=busy_figurehead.get(b.registrant)
            #     tempo=b.make_temp_o()
            #     fig_busy.append(tempo)
            # else:
            #     r_busy=busy.get(b.registrant)
            #     tempo=b.make_temp_o()
            #     r_busy.append(tempo)

        for r in relevant_reg:
            hard_conflict = []
            soft_conflict = []

            occur_list1 = busy1.get(r)
            occur_list2 = busy2.get(r)

            for o in occur_list1:
                for o2 in (occur_list2 + occur_list1):
                    # Compares active occurrences with passive occurrences,
                    # blackouts, as well as other acive occurrences
                    if o != o2:
                        if o.os_hard_intersect(o2):
                            if o2 not in hard_conflict:
                                hard_conflict.append(o2)
                            if o not in hard_conflict:
                                hard_conflict.append(o)
                        elif o.os_soft_intersect(o2):
                            if (o2 not in soft_conflict):
                                soft_conflict.append(o2)
                            if (o not in soft_conflict):
                                soft_conflict.append(o)

            if len(hard_conflict) > 0:
                hard_conflict.sort(key=lambda o:(o.start_time, o.end_time))
                relevant_hard_conflicts.append({r:hard_conflict})
            if len(soft_conflict) > 0:
                soft_conflict.sort(key=lambda o:(o.start_time, o.end_time))
                relevant_soft_conflicts.append({r:soft_conflict})

    #elapsed = datetime.now()-start
    return render(request, template, {
        'con':con,
        'active':active,
        'relevant_conflicts':[relevant_hard_conflicts, relevant_soft_conflicts],
        'coach_search':coach_search,
        'captain_search':captain_search,
        'registrant_search':registrant_search

    })

#-------------------------------------------------------------------------------
@login_required
def location_view(
    request,
    template='swingtime/location_view.html',
    con_id=None,
    loc_id=None,
    **extra_context
):
    con=None
    location=None
    date_range=None

    if loc_id:
        try:
            location = Location.objects.get(pk=int(loc_id))
            if con_id:
                con = Con.objects.get(pk=con_id)
            else:
                con = Con.objects.most_upcoming()
            con_locs = con.get_locations()
            con_i = con_locs.index(location)
            try:
                next_loc=con_locs[con_i + 1]
            except:
                next_loc=con_locs[0]
            try:
                prev_loc = con_locs[con_i - 1]
            except:
                prev_loc = con_locs[-1]
            date_range = con.get_date_range()
        except ObjectDoesNotExist:
            pass

    by_location=Occurrence.objects.filter(
            start_time__gte=con.start,
            end_time__lte=con.end,
            location=location
            )

    return render(request, template, {
        'con':con,
        'location':location,
        'by_location': by_location,
        'next_loc': next_loc,
        'prev_loc': prev_loc,

    })

#-------------------------------------------------------------------------------
@login_required
def chal_submit(
    request,
    template='swingtime/chal_submit.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()
    # in 2016 included accpted, Ivanna complained too many.
    # for 2017 trying to filter out, only do ones w/no decision.
    #q = (Challenge.objects.filter(con=con, RCrejected=False)
    q = (Challenge.objects.filter(con=con, RCaccepted=False, RCrejected=False)
            .exclude(roster1=None)
            .exclude(roster2=None)
            .exclude(submitted_on=None)
            .order_by('submitted_on')
            )
    q_od = OrderedDict()

    data = []
    for c in q:
        thisdict = {"name": c, "skill_display": c.skill_display(),
                "activity_type": c.get_activity_type(), "location_type": c.location_type,
                "duration": c.get_duration_display(), "submitted_on": c.submitted_on
                }
        form = ChalStatusForm(request.POST or None, instance=c,prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            chal = dic.get("name")
            if not chal.RCrejected and not chal.RCaccepted:
                sort_data.append(dic)
        data = sort_data  #to remove recently rejected.

    table = ChallengeTable(data)
    RequestConfig(request,paginate={"per_page": 300}).configure(table)

    new_context = {"table": table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def chal_accept(
    request,
    template='swingtime/chal_accept.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    q = (Challenge.objects.filter(con=con, RCaccepted=True)
            .exclude(submitted_on=None).order_by('submitted_on')
            )
    #q_od = collections.OrderedDict()
    q_od = OrderedDict()
    data = []
    for c in q:
        thisdict = {"name": c, "skill_display": c.skill_display(),
                "activity_type": c.get_activity_type(), "location_type": c.location_type,
                "duration": c.get_duration_display(), "submitted_on": c.submitted_on
                }
        form = ChalStatusForm(request.POST or None, instance=c,prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            chal = dic.get("name")
            if chal.RCaccepted:
                sort_data.append(dic)
        data = sort_data  #to remove recently rejected.

    table = ChallengeTable(data)
    RequestConfig(request,paginate={"per_page": 300}).configure(table)
    new_context={'table': table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def chal_reject(
    request,
    template='swingtime/chal_reject.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    q = (Challenge.objects.filter(con=con, RCrejected=True)
            .exclude(submitted_on=None).order_by('submitted_on'))
    q_od = OrderedDict()
    data = []
    for c in q:
        thisdict = {"name": c, "skill_display": c.skill_display(),
                "activity_type": c.get_activity_type(), "location_type": c.location_type,
                "duration": c.get_duration_display(), "submitted_on": c.submitted_on
                }
        form = ChalStatusForm(request.POST or None, instance=c, prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            chal = dic.get("name")
            if chal.RCrejected:
                sort_data.append(dic)
        data = sort_data  #to remove recently ineligible.

    table = ChallengeTable(data)
    RequestConfig(request,paginate = {"per_page": 300}).configure(table)
    new_context = {"table": table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def train_submit(
    request,
    template='swingtime/train_submit.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()
    # in 2016 included accpted, Ivanna complained too many.
    # for 2017 trying to filter out, only do ones w/no decision.
    #q = Training.objects.filter(con=con, RCrejected=False).order_by('created_on')
    q = Training.objects.filter(con=con, RCaccepted=False, RCrejected=False).order_by('created_on')
    q_od = OrderedDict()
    data = []
    for c in q:
        thisdict = {"name": c, "coach": c.figurehead_display, "skill":c.skill_display(),
                "onsk8s": c.onsk8s, "contact": c.contact, "location_type": c.location_type,
                "duration": c.get_duration_display(), "created_on": c.created_on
                }
        form = TrainStatusForm(request.POST or None, instance=c, prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            train = dic.get("name")
            if not train.RCrejected and not train.RCaccepted:
                sort_data.append(dic)
        data = sort_data  #to remove recently rejected.

    table = TrainingTable(data)
    RequestConfig(request, paginate={"per_page": 300}).configure(table)

    new_context = {"table": table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def train_accept(
    request,
    template='swingtime/train_accept.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    q = Training.objects.filter(con=con, RCaccepted=True).order_by('created_on')
    q_od = OrderedDict()
    data = []
    for c in q:
        thisdict = {"name": c, "coach": c.figurehead_display, "skill": c.skill_display(),
                "onsk8s": c.onsk8s, "contact": c.contact, "location_type": c.location_type,
                "duration": c.get_duration_display(), "created_on":c.created_on
                }
        form = TrainStatusForm(request.POST or None, instance=c, prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            train = dic.get("name")
            if train.RCaccepted:
                sort_data.append(dic)
        data = sort_data  #to remove recently changed.

    table = TrainingTable(data)
    RequestConfig(request, paginate={"per_page": 300}).configure(table)

    new_context = {"table": table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def train_reject(
    request,
    template='swingtime/train_reject.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    q = Training.objects.filter(con=con, RCrejected=True).order_by('created_on')
    q_od = OrderedDict()
    data = []
    for c in q:
        thisdict = {"name": c, "coach": c.figurehead_display, "skill": c.skill_display(),
                "onsk8s": c.onsk8s, "contact": c.contact, "location_type": c.location_type,
                "duration": c.get_duration_display(), "created_on":c.created_on
                }
        form = TrainStatusForm(request.POST or None, instance=c, prefix=str(c.pk))
        thisdict["status"] = form
        data.append(thisdict)
        q_od[c] = form

    save_success = 0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance = form.save()
                save_success += 1
        sort_data = []
        for dic in data:
            train = dic.get("name")
            if train.RCrejected:
                sort_data.append(dic)
        data = sort_data  #to remove recently changed.

    table = TrainingTable(data)
    RequestConfig(request,paginate={"per_page": 300}).configure(table)

    new_context = {"table": table, "save_success": save_success, "q_od": q_od,
            "con": con, "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------

@login_required
def act_unsched(
    request,
    template='swingtime/act_unsched.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    """Hideous view. Readability sacraficed for speed."""

    activities = []
    level1pairs = {}
    save_attempt = False
    save_success = False
    added2schedule = []
    act_types = ["challenge", "training"]
    prefix_base = ""
    cycle = -1
    possibles = []

    if request.method == 'POST':
        post_keys=dict(request.POST).keys()

        if 'Auto_Chal' in request.POST or 'Auto_Train' in request.POST:
            pk_list = []

            if 'Auto_Chal' in request.POST:
                for k in post_keys:
                    lsplit = k.split("-")
                    prefix_base = 'challenge'
                    if lsplit[0] == prefix_base:
                        pk_list.append(int(lsplit[1]))
                # Uglu, but only 1 db hit, evaluated later
                possibles = (Challenge.objects
                        .filter(pk__in=pk_list)
                        .select_related('roster1')
                        .select_related('roster2')
                        .select_related('roster1__captain')
                        .prefetch_related('roster1__participants')
                        .select_related('roster2__captain')
                        .prefetch_related('roster2__participants')
                        )
            elif 'Auto_Train' in request.POST:
                for k in post_keys:
                    lsplit = k.split("-")
                    prefix_base = 'training'
                    if lsplit[0] == prefix_base:
                        pk_list.append(int(lsplit[1]))
                #Ugly but only 2 hits pet training, evaluated later
                possibles = (Training.objects
                        .filter(pk__in=pk_list)
                        .prefetch_related('coach')
                        .prefetch_related('coach__user')
                        .prefetch_related('coach__user__registrant_set')
                        )

            # If want to rewrite Otto, start here with getting possibles,
            all_act_data = {}

            for act in possibles:
                if act.is_a_challenge():
                    figureheads = [act.roster1.captain ,act.roster2.captain]
                    participants = (list(act.roster1.participants.all())
                            + list(act.roster2.participants.all())
                            )
                    all_act_data[act] = {'figureheads': figureheads, 'participants': participants}
                elif act.is_a_training():
                    participants = []
                    for c in act.coach.all():
                        participants+=list(c.user.registrant_set.filter(con=con))
                    all_act_data[act] = {'figureheads': participants, 'participants': participants}

            all_act_data = Occurrence.objects.gather_possibles(con, all_act_data)
            level1pairs = Occurrence.objects.sort_possibles(con, all_act_data, level1pairs, prefix_base)

            new_context = {"added2schedule": added2schedule,
                    "save_attempt": save_attempt,"save_success": save_success,
                    "level1pairs": level1pairs, "activities": activities,
                    "con": con, "con_list": Con.objects.all()
                    }
            extra_context.update(new_context)
            return render(request, template, extra_context)

        else:  #if neither 'Auto_Chal' nor 'Auto_Train' in request.POST
            if 'save schedule' in request.POST:
                save_attempt = True
                for k in post_keys:
                    lsplit = k.split("-")
                    if len(lsplit) == 5 and lsplit[4] == 'add2sched':
                        o = Occurrence.objects.get(pk=int(lsplit[3]))
                        if lsplit[0] == "challenge":
                            a = Challenge.objects.get(pk=int(lsplit[1]))
                            o.challenge = a
                        elif lsplit[0]=="training":
                            a = Training.objects.get(pk=int(lsplit[1]))
                            o.training = a
                        o.save()
                        added2schedule.append(o)
                        save_success = True
    # If not post, or just saves
    cfilter = list(Challenge.objects
            .filter(con=con, RCaccepted=True)
            .select_related('roster1__captain')
            .select_related('roster2__captain')
            .prefetch_related('occurrence_set')
            )
    tfilter = list(Training.objects
            .filter(con=con, RCaccepted=True)
            .prefetch_related('coach__user__registrant_set')
            .prefetch_related('occurrence_set')
            )

    for q in [cfilter, tfilter]:
        cycle += 1
        temp_dict = {}
        for obj in q:
            if ((obj.is_a_training() and obj.sessions and len(obj.occurrence_set.all()) < obj.sessions) or
                    (len(obj.occurrence_set.all()) <= 0)
                    ):

                score = len(obj.get_figurehead_blackouts())
                if score not in temp_dict:
                    temp_dict[score] = [obj]
                else:
                    this_list = temp_dict.get(score)
                    this_list.append(obj)
                    temp_dict[score] = list(this_list)
        score_list = temp_dict.keys()
        score_list.sort(reverse=True)
        od_list = []
        for score in score_list:
            temp_list = temp_dict.get(score)
            for act in temp_list:
                od = OrderedDict()
                od["act"] = act
                od["score"] = score
                od["check_form"] = ActCheck(prefix=(act_types[cycle] + "-" + str(act.pk)))
                od_list.append(od)
        activities.append(od_list)

    new_context = {"added2schedule": added2schedule, "save_attempt": save_attempt,
            "save_success": save_success, "level1pairs": level1pairs,
            "activities": activities ,"con": con, "con_list": Con.objects.all()
            }

    extra_context.update(new_context)

    return render(request, template, extra_context)

#-------------------------------------------------------------------------------

@login_required
def act_sched(
    request,
    template='swingtime/act_sched.html',
    con_id=None,
    **extra_context
):
    if con_id:
        con = Con.objects.get(pk=con_id)
    else:
        con = Con.objects.most_upcoming()

    challenges = Occurrence.objects.filter(challenge__con=con)
    trainings = Occurrence.objects.filter(training__con=con)

    new_context = {"activities": [challenges, trainings], "con": con,
            "con_list": Con.objects.all()
            }
    extra_context.update(new_context)
    return render(request, template, extra_context)

#-------------------------------------------------------------------------------
@login_required
def sched_status(
    request,
    template='swingtime/sched_status.html',
    con_id=None,
    form_class=ConSchedStatusForm,
    save_success=False
):
    if con_id:
        con = get_object_or_404(Con, pk=con_id)
    else:
        con = get_object_or_404(Con, pk=Con.objects.most_upcoming().pk)
    c_no_os = []
    t_no_os = []
    cull_attempt = False
    cull_success = False

    if request.method == 'POST':

        if "sched_stus_form" in request.POST:
            form = form_class(request.POST, instance=con)
            if form.is_valid():
                form.save()
                save_success=True
        elif "cull_form" in request.POST:
            form = form_class(instance=con)
            c_no_os, t_no_os = con.get_unscheduled_acts()
            cull_attempt = True
            if "confirm_delete" in request.POST:
                for c in c_no_os:
                    c.delete()
                for t in t_no_os:
                    t.delete()
                # Refresh to confirm nothing left
                c_no_os, t_no_os = con.get_unscheduled_acts()
                cull_success = True

    else:  # If not post, just return form
        form = form_class(instance=con)

    context_dict = {"cull_success": cull_success, "cull_attempt": cull_attempt,
            "c_no_os": c_no_os, "t_no_os": t_no_os, 'save_success': save_success,
            'con': con, 'con_list': Con.objects.all(), 'form': form
            }

    return render(request, template, context_dict)

#-------------------------------------------------------------------------------
@login_required
def sched_assist_tr(
    request,
    act_id,
    template='swingtime/sched_assist.html',
    makedummies=False
):
    try:
        act = Training.objects.get(pk=act_id)
    except:
        return render(request, template, {})

    if "level" in request.GET:
        level = int(request.GET['level'])
    else:
        level = 1

    if request.method == 'POST':
        if 'save_activity' in request.POST:
            form = TInterestForm(request.POST,instance=act)
            if form.is_valid():
                form.save()
        elif "makedummies" in request.POST:
            form = TInterestForm(instance=act)
            makedummies = True
    else:
        form = TInterestForm(instance=act)

    slots = act.sched_conflict_score(level=level, makedummies=makedummies)

    context_dict = {'level': level, 'form': form, 'act': act, 'slots': slots,
            'training': act, 'challenge': None
            }

    return render(request, template, context_dict)

#-------------------------------------------------------------------------------
@login_required
def sched_assist_ch(
    request,
    act_id,
    template='swingtime/sched_assist.html',
    makedummies=False
):

    try:
        act = Challenge.objects.get(pk=act_id)
    except:
        return render(request, template, {})
    if "level" in request.GET:
        level = int(request.GET['level'])
    else:
        level = 1

    if request.method == 'POST':
        if 'save_activity' in request.POST:
            form = CInterestForm(request.POST,instance=act)
            if form.is_valid():
                form.save()
        elif "makedummies" in request.POST:
            makedummies = True
            form = CInterestForm(instance=act)
    else:
        form = CInterestForm(instance=act)

    slots = act.sched_conflict_score(level=level, makedummies=makedummies)

    context_dict = {'level': level, 'form': form, 'act': act,
            'slots': slots, 'training' :None, 'challenge': act
            }

    return render(request, template, context_dict)

#-------------------------------------------------------------------------------
@login_required
def calendar_home(
    request,
    template='calendar_home.html',
    **extra_context
):

    return render(request, template, extra_context)

#-------------------------------------------------------------------------------

@login_required
def occurrence_view(
    request,
    pk,
    template='swingtime/occurrence_detail.html',
    form_class=forms.SingleOccurrenceForm,
    save_success=False
):
    '''
    View a specific occurrence and optionally handle any updates.

    Context parameters:

    ``occurrence``
        the occurrence object keyed by ``pk``

    ``form``
        a form object for updating the occurrence
    '''
    occurrence = get_object_or_404(Occurrence, pk=pk)
    conflict_free = False
    conflict = {}
    get_dict = {}
    if "training" in request.GET and request.GET['training'] not in no_list:
        training = Training.objects.get(pk=request.GET['training'])
        get_dict['training'] = training
    if "challenge" in request.GET and request.GET['challenge'] not in no_list:
        challenge = Challenge.objects.get(pk=request.GET['challenge'])
        get_dict['challenge'] = challenge

    if request.method == 'POST':
        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            if "update" in request.POST:
                form.save()
                save_success = True
            elif "check" in request.POST:
                figurehead_conflict = occurrence.figurehead_conflict()
                if figurehead_conflict:
                    conflict["figurehead_conflict"] = figurehead_conflict
                participant_conflict = occurrence.participant_conflict()
                if participant_conflict:
                    conflict["participant_conflict"] = participant_conflict
                blackout_conflict = occurrence.blackout_conflict()
                if blackout_conflict:
                    conflict["blackout_conflict"] = blackout_conflict
                if len(conflict) <= 0:
                    conflict_free = True
            elif "delete" in request.POST:
                if occurrence and occurrence.location:
                    # Keep location after occurrence gets deleted
                    lpk = int(occurrence.location.pk)
                    date = datetime.date(occurrence.start_time)
                    occurrence.delete()
                    return redirect(
                            'swingtime-daily-location-view',
                            lpk, date.year, date.month, date.day
                            )

    else:
        form = form_class(instance=occurrence,initial=get_dict)

    try:
        location = occurrence.location
    except:
        location = None

    context_dict = {'location': location, 'conflict_free': conflict_free,
            'conflict': conflict, 'save_success': save_success,
            'occurrence': occurrence, 'form': form
            }
    return render(request, template, context_dict)


#-------------------------------------------------------------------------------
@login_required
def add_event(
    request,
    template='swingtime/add_event.html',
    recurrence_form_class=forms.SingleOccurrenceForm,
):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.

    Context parameters:

    ``dtstart``
        a datetime.datetime object representing the GET request value if present,
        otherwise None

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences

    '''
    save_success = False
    dtstart = None
    drend = None
    training = None
    challenge = None
    location = None
    conflict = {}
    conflict_free = False
    recurrence_dict = {}
    get_dict = {}

    # Fetch all get values as intials
    if 'dtstart' in request.GET:
        try:
            dtend = dtstart = parser.parse(request.GET['dtstart'])
            get_dict["start_time"] = dtstart
            recurrence_dict["start_time"] = dtstart
            recurrence_dict["end_time"] = dtend
        except(TypeError, ValueError) as exc:
            # TODO: A badly formatted date is passed to add_event
            logging.warning(exc)
    if "location" in request.GET and request.GET['location'] not in no_list:
        location = Location.objects.get(pk=request.GET['location'])
        get_dict['location'] = location
        recurrence_dict['location'] = location
    if "training" in request.GET and request.GET['training'] not in no_list:
        training = Training.objects.get(pk=request.GET['training'])
        get_dict['training'] = training
        recurrence_dict['training'] = training
    if "challenge" in request.GET and request.GET['challenge'] not in no_list:
        challenge = Challenge.objects.get(pk=request.GET['challenge'])
        get_dict['challenge'] = challenge
        recurrence_dict['challenge'] = challenge
    # Done fetching get values

    recurrence_form = recurrence_form_class(initial=recurrence_dict, date=dtstart)

    if request.method == 'POST':

        dtend_post = [u'end_time_1', u'end_time_0_year', u'end_time_0_month', 'end_time_0_day']
        if len( set(dtend_post).intersection(request.POST.keys())) > 0:
            dtend_str = (request.POST['end_time_0_year']
                    + "-" + request.POST['end_time_0_month']
                    + "-" + request.POST['end_time_0_day']
                    + "T" + request.POST['end_time_1']
                    )
            dtend = parser.parse(dtend_str)

        # Will override the train/chal set from get, if they're there.
        if "challenge" in request.POST and request.POST['challenge'] not in no_list:
            challenge = Challenge.objects.get(pk=request.POST['challenge'])
        if "training" in request.POST and request.POST['training'] not in no_list:
            training = Training.objects.get(pk=request.POST['training'])

        recurrence_form = recurrence_form_class(request.POST)

        if recurrence_form.is_valid():
            occurrence = recurrence_form.save(commit=False)

            if occurrence.end_time <= occurrence.start_time:
                occurrence.end_time = occurrence.get_endtime()
            # To keep calculated end time if conflict
            recurrence_form = recurrence_form_class(instance=occurrence)

            if ("check" in request.POST):
                figurehead_conflict = occurrence.figurehead_conflict()
                if figurehead_conflict:
                    conflict["figurehead_conflict"] = figurehead_conflict
                participant_conflict=occurrence.participant_conflict()
                if participant_conflict:
                    conflict["participant_conflict"] = participant_conflict
                blackout_conflict = occurrence.blackout_conflict()
                if blackout_conflict:
                    conflict["blackout_conflict"] = blackout_conflict
                if len(conflict) <= 0:
                    conflict_free = True

            if ("save" in request.POST):
                occurrence.save()
                # Important, otherwise can make new ones forever and think editing same one
                return redirect('swingtime-occurrence', occurrence.id)

    # Happens regardless of post or not
    context_dict = {'conflict_free': conflict_free, 'conflict': conflict,
            'dtstart': dtstart, 'single_occurrence_form': recurrence_form
            }

    return render(request, template, context_dict)

#-------------------------------------------------------------------------------
@login_required
def _datetime_view(
    request,
    template,
    dt,
    loc_id=None,
    timeslot_factory=None,
    items=None,
    params=None,
    lcat=None,
    ltype=None
):
    '''
    Build a time slot grid representation for the given datetime ``dt``. See
    utils.create_timeslot_table documentation for items and params.

    Context parameters:

    ``day``
        the specified datetime value (dt)

    ``next_day``
        day + 1 day

    ``prev_day``
        day - 1 day

    ``timeslots``
        time slot grid of (time, cells) rows

    '''
    timeslot_factory = timeslot_factory or utils.create_timeslot_table
    params = params or {}

    try:
        con = Con.objects.get(start__lte=dt, end__gte=dt)
        con_id = con.pk
        all_locations = con.get_locations()

        if loc_id:
            locations = [Location.objects.get(pk=int(loc_id))]
        elif lcat or ltype:
            venues = list(con.venue.all())
            if lcat and int(lcat) < len(LOCATION_CATEGORY_FILTER):
                ind = int(lcat)
                loc_cat = LOCATION_CATEGORY_FILTER[ind][1]
                base_q = Location.objects.filter(
                        venue__in=venues, location_category__in=loc_cat
                        )
            elif ltype and int(ltype)<len(LOCATION_TYPE_FILTER):
                ind = int(ltype)
                loc_type = LOCATION_TYPE_FILTER[ind][1]
                base_q = Location.objects.filter(
                        venue__in=venues, location_type__in=loc_type
                        )
            else:
                base_q = Location.objects.filter(venue__in=venues)
            locations = list(base_q)
        else:
            locations = con.get_locations()

    except ObjectDoesNotExist:
        con = None
        con_id = None
        all_locations = []
        locations = []

    return render(request, template, {
        'day':       dt,
        'con':       con,
        'con_id':  con_id,
        'locations': locations,
        'loc_id':loc_id,
        'LOCATION_TYPE':LOCATION_TYPE,
        'LOCATION_CATEGORY':LOCATION_CATEGORY,
        'maxwidth': 99/(len(locations)+1),
        'next_day':  dt + timedelta(days=+1),
        'prev_day':  dt + timedelta(days=-1),
        'timeslots': timeslot_factory(
                dt=dt, items=items, loc_id=loc_id,
                lcat=lcat, ltype=ltype, **params
                )
    })


#-------------------------------------------------------------------------------
@login_required
def day_view(request, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    if "category" in request.GET:
        lcat = request.GET['category']
    else:
        lcat = None

    if "type" in request.GET:
        ltype = request.GET['type']
    else:
        ltype = None
    dt = datetime(int(year), int(month), int(day))

    return _datetime_view(request, template, dt, lcat=lcat, ltype=ltype,**params)


#-------------------------------------------------------------------------------
@login_required
def day_location_view(request, loc_id, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    dt = datetime(int(year), int(month), int(day))
    return _datetime_view(request, template, dt, loc_id, **params)

#-------------------------------------------------------------------------------
@login_required
def day_clone(request, con_id=None, template='swingtime/day_clone.html', **params):
    """This give soption to clone 1 day's Occurrence settings to another.
    It will not overwrite anything that already exists, only if time is available.
    Makes empty occurrences, does not move chal/train over, but does retain interest.
    Only for current con, can't clone days from a past con.
    """

    save_attempt = False
    save_succes = []

    if con_id:
        try:
            con = Con.objects.get(pk=con_id)
        except:
            return render(request, template, {})
    else:
        con = Con.objects.most_upcoming()

    form = DLCloneForm(
            request.POST or None,
            date_list=con.get_date_range(),
            loc_list=con.get_locations()
            )

    if request.method == 'POST':  # There's only one post option
        save_attempt = True
        fromdate = parse(request.POST['fromdate']).date()
        from_start = fromdate
        from_end = (fromdate + timedelta(days=1))
        fromlocation = Location.objects.get(pk=request.POST['fromlocation'])
        todate = parse(request.POST['todate']).date()
        tolocation = Location.objects.get(pk=request.POST['tolocation'])

        sample_slots = Occurrence.objects.filter(
                start_time__gte=fromdate,
                end_time__lt=from_end,
                location=fromlocation
                )

        for s in sample_slots:
            target_start = datetime(
                    year=todate.year, month=todate.month, day=todate.day,
                    hour=s.start_time.hour,minute=s.start_time.minute
                    )
            target_end = datetime(
                    year=todate.year, month=todate.month, day=todate.day,
                    hour=s.end_time.hour ,minute=s.end_time.minute
                    )

            if tolocation.is_free(target_start, target_end):
                clone = Occurrence(
                        start_time=target_start,
                        end_time=target_end,
                        interest=s.interest,
                        location=tolocation
                        )
                save_succes.append(clone)
                clone.save()

        context_dict = {'todate': todate, 'tolocation': tolocation, 'form': form,
                'save_succes': save_succes, 'save_attempt': save_attempt,
                }

        return render(request, template, context_dict)

    #only runs if not post
    context_dict = {'save_succes': save_succes, 'save_attempt': save_attempt, 'form': form}

    return render(request, template, context_dict)


#-------------------------------------------------------------------------------

@login_required
def today_view(request, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    return _datetime_view(request, template, datetime.now(), **params)


#-------------------------------------------------------------------------------
@login_required
def year_view(request, year, template='swingtime/yearly_view.html', queryset=None):
    '''

    Context parameters:

    ``year``
        an integer value for the year in questin

    ``next_year``
        year + 1

    ``last_year``
        year - 1

    ``by_month``
        a sorted list of (month, occurrences) tuples where month is a
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months
        which have at least 1 occurrence is represented in the list

    '''
    year = int(year)
    queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
    occurrences = queryset.filter(
        models.Q(start_time__year=year) |
        models.Q(end_time__year=year)
    )

    def group_key(o):
        return datetime(
            year,
            o.start_time.month if o.start_time.year == year else o.end_time.month,
            1
        )

    return render(request, template, {
        'year': year,
        'by_month': [(dt, list(o)) for dt,o in itertools.groupby(occurrences, group_key)],
        'next_year': year + 1,
        'last_year': year - 1

    })


#-------------------------------------------------------------------------------
@login_required
def month_view(
    request,
    year,
    month,
    template='swingtime/monthly_view.html',
    queryset=None
):
    '''
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:

    ``today``
        the current datetime.datetime value

    ``calendar``
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day

    ``this_month``
        a datetime.datetime representing the first day of the month

    ``next_month``
        this_month + 1 month

    ``last_month``
        this_month - 1 month

    '''
    year, month = int(year), int(month)
    cal         = calendar.monthcalendar(year, month)
    dtstart     = datetime(year, month, 1)
    last_day    = max(cal[-1])
    dtend       = datetime(year, month, last_day)

    # TODO Whether to include those occurrences that started in the previous
    # month but end in this month?
    queryset = queryset._clone() if queryset is not None else Occurrence.objects.select_related()
    occurrences = queryset.filter(start_time__year=year, start_time__month=month)

    def start_day(o):
        return o.start_time.day

    by_day = dict([(dt, list(o)) for dt,o in itertools.groupby(occurrences, start_day)])
    data = {
        'today':      datetime.now(),
        'calendar':   [[(d, by_day.get(d, [])) for d in row] for row in cal],
        'this_month': dtstart,
        'next_month': dtstart + timedelta(days=+last_day),
        'last_month': dtstart + timedelta(days=-1),
    }

    return render(request, template, data)
