from collections import OrderedDict
#import datetime
from datetime import timedelta, date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
#from django.shortcuts import render, render_to_response, redirect
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.utils import timezone

from con_event.forms import EligibleRegistrantForm,SearchForm
from con_event.models import Con, Registrant
import django_tables2 as tables
#from django_tables2 import RequestConfig
from rcreg_project.extras import remove_punct, ascii_only ,ascii_only_no_punct
from scheduler.app_settings import (MAX_CAPTAIN_LIMIT, CLOSE_CHAL_SUB_AT,
        DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION,
        DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION
        )
from scheduler.forms import (CommunicationForm, MyRosterSelectForm,
        GameRosterCreateModelForm, GameModelForm, CoachProfileForm, SendEmail,
        ChallengeModelForm, ChallengeRosterModelForm, TrainingModelForm,
        DurationOnly, ScoreFormDouble, GenderSkillForm
        )

from scheduler.models import Coach, Roster, Challenge, Training, GAMETYPE
from scheduler.tables import RosterTable
from swingtime.models import Occurrence,TrainingRoster


no_list = ["" ,u'', None, "None"]

#-------------------------------------------------------------------------------
@login_required
def my_schedule(request):
    """Used for Registrants to see My Schedule.
    If registrant or user in get and User is a boss, can also be used to see
    other people's schedules. If not the boss, ignores and shows you your own.
    """

    user = request.user
    spoof_reg = None
    spoof_user = None
    spoof_error = False
    registrant_dict_list = []

    if user.is_the_boss() and (
            "registrant" in request.GET or "user" in request.GET
            ):

        if "user" in request.GET:  # and is the boss
            try:
                spoof_user = User.objects.get(pk=request.GET['user'])
                registrant_list = list(spoof_user.registrant_set.all())
            except ObjectDoesNotExist:
                spoof_error = True
                registrant_list = list(user.registrant_set.all())

        elif "registrant" in request.GET:  # and is the boss
            try:
                spoof_reg = Registrant.objects.get(pk=request.GET['registrant'])
                registrant_list = [spoof_reg]
            except ObjectDoesNotExist:
                spoof_error = True
                registrant_list = list(user.registrant_set.all())
    else:
        # If not the boss, will always return user's own schedule
        registrant_list = list(user.registrant_set.all())

    # Happens whether is registrant checking own schedule or boss spoofs others'
    if not spoof_error:
        active = registrant_list[0].con  # Most recent/upcoming registrant con
        for registrant in registrant_list:
            registrant_dict = {
                    'con': registrant.con,
                    'registrant': registrant,
                    'reg_os': registrant.get_occurrences()
                    }
            registrant_dict_list.append(registrant_dict)

    context_dict = {
            'spoof_error': spoof_error,
            'spoof_user': spoof_user,
            'spoof_reg': spoof_reg,
            'active': active,
            'registrant_dict_list': registrant_dict_list,
            }

    return render_to_response(
            'my_schedule.html',
            context_dict ,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def email_captain(request, roster_id):
    """Form will only show if captain has agreed to accept emails and
    has a user and user has an email address.
    By default all registrant should have users and email addresses.
    But who knows, maybe one will get deleted.
    """

    user = request.user
    roster = Roster.objects.get(pk=roster_id)
    form = SendEmail(request.POST or None)

    if request.method == "POST":
        message=request.POST['message']
        email_attempt = True
        email_success = roster.email_captain(user, message)
    else:
        email_attempt = False
        email_success = False

    context_dict = {
            'email_attempt': email_attempt,
            'email_success': email_success,
            'form': form,
            'roster': roster
            }
    return render_to_response(
            'email_captain.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def coach_profile(request):
    """For coaches to see and edit own profile.
    Other users can view coach data via 'view_coach'.
    """

    save_attempt = False
    save_success = False
    user = request.user

    try:
        coach = Coach.objects.get(user=user)
    except ObjectDoesNotExist:
        coach = None

    form = CoachProfileForm(request.POST or None, instance=coach)

    if request.method == 'POST':
        save_attempt = True
        if form.is_valid():
            form.save()
            save_success = True

    context_dict = {
            'coach': coach,
            'form': form,
            'save_attempt': save_attempt,
            'save_success': save_success,
            'user':user
            }

    return render_to_response(
            'coach_profile.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def email_coach(request, coach_id):
    """Form will only show if coach has agreed to accept emails and
    has a user and user has an email address.
    By default all registrant should have users and email addresses.
    But who knows, maybe one will get deleted.
    """

    user = request.user
    form = SendEmail(request.POST or None)
    try:
        coach = Coach.objects.get(pk=int(coach_id))
    except ObjectDoesNotExist:
        coach = None

    if request.method == "POST":
        message=request.POST['message']
        email_attempt = True
        email_success = coach.email_coach(user, message)
    else:
        email_attempt = False
        email_success = False

    context_dict = {
            'email_attempt': email_attempt,
            'email_success': email_success,
            'form': form,
            'coach':coach
            }
    return render_to_response(
            'email_coach.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
def view_coach(request, coach_id):
    """For anyone to view coach description, trainings, and possibly email."""

    try:
        coach = Coach.objects.get(pk=coach_id)
    except ObjectDoesNotExist:
        coach = None

    context_dict = {'coach': coach}

    return render_to_response(
            'view_coach.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
def view_training(request, activity_id, o_id=None):
    """If no Occurrence, just displays the training and coach data.
    If schedule is visible and there is an Occurrence,
    that info will be available.
    """

    user = request.user
    occur = None
    rosters = []

    # For Volunteer and Bosses, if want to download an excel of training data.
    if 'download_excel' in request.POST:
        downo = Occurrence.objects.get(pk=int(request.POST['downo_id']))
        wb, xlfilename = downo.excel_backup()
        response = HttpResponse(
                content_type='application/vnd.openxmlformats\
                        -officedocument.spreadsheetml.sheet'
                )
        response['Content-Disposition'] = (
                'attachment; filename=%s' % (xlfilename)
                )
        wb.save(response)
        return response

    # Otherwise, if not downloading excel
    try:
        training = Training.objects.get(pk=int(activity_id))
    except ObjectDoesNotExist:
        training = None

    if training:
        visible = training.con.sched_visible
        if visible:
            if o_id:
                try:
                    occur = Occurrence.objects.get(
                            training=training,
                            pk=int(o_id)
                            )
                except ObjectDoesNotExist:
                    occur = None

            Tos = list(Occurrence.objects.filter(training=training))
            # If there's only 1 ocurrence, it's same as if o_id were supplied
            if not occur and len(Tos) == 1:
                occur = Tos[0]

            if occur:
                registered, rcreated = TrainingRoster.objects.get_or_create(
                        registered=occur
                        )
                auditing, acreated = TrainingRoster.objects.get_or_create(
                        auditing=occur
                        )
                rosters = [registered, auditing]

        else:
            Tos = []  # If schedule not visible, occurrenece list empty.

        context_dict = {
                'occur': occur,
                'Tos': Tos,
                'visible': visible,
                'user': user,
                'training': training,
                'rosters': rosters
                }
    else:  # if no training
        context_dict = {}

    return render_to_response(
            'view_training.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
def trainings_home(request, con_id=None):

    if con_id:
        try:
            con = Con.objects.get(pk=con_id)
        except ObjectDoesNotExist:
            con = Con.objects.most_upcoming()
    else:
        con = Con.objects.most_upcoming()

    scheduled = list(Occurrence.objects.filter(
            training__con=con)
            )

    if len(scheduled) > 0 and con.sched_visible:
        date_dict = OrderedDict()
        # a benefit of making the date_dict by con date range is
        # a throwaway occurence can be made for volunteers to practice on
        # but won't show on the site, as long as it's not within con date range
        for day in con.get_date_range():
            date_dict[day] = []

        for o in scheduled:
            if o.start_time.date() in date_dict:
                temp_list = date_dict.get(o.start_time.date())
                temp_list.append(o)
                date_dict[o.start_time.date()] = list(temp_list)

        for v in date_dict.values():
            v.sort(key=lambda o: o.start_time)
    else:
        date_dict = None

    context_dict = {
            'con': con,
            'con_list': list(Con.objects.all()),
            'date_dict': date_dict
            }

    return render_to_response(
            'trainings_home.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def my_trainings(request):
    """Shows submitted trainings user is listed as coach for.
    Does not show trainings one registered to attend. Just coaching.
    """

    user = request.user
    registrant_list = list(user.registrant_set.all())
    most_upcoming = Con.objects.most_upcoming()
    registrant_dict_list = []

    for registrant in registrant_list:
        coach = user.is_a_coach()
        if coach:
            my_trains = coach.training_set.filter(con=registrant.con)
        else:
            my_trains=None

        registrant_dict={
                'con': registrant.con,
                'registrant': registrant,
                'my_trains': my_trains
                }
        registrant_dict_list.append(registrant_dict)

    if len(registrant_list) > 0:
        active = registrant_list[0].con
    else:
        active = None

    context_dict = {
            'active': active,
            'user': user,
            'registrant_dict_list': registrant_dict_list
            }

    return render_to_response(
            'my_trainings.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def propose_new_training(request):

    user = request.user
    upcoming_registrants=user.upcoming_registrants()
    trainings_coached = user.trainings_coached()
    add_fail = False
    training_made = False
    formlist = []
    most_upcoming_con = Con.objects.most_upcoming()

    if request.method == "POST":

        if 'duration' in request.POST:  # Only offered for off-skates
            training_made = Training.objects.get(pk=request.POST['training_id'])
            training_made.duration = request.POST['duration']
            training_made.save()
            context_dict = {'add_fail': add_fail, 'training_made': training_made,'upcoming_registrants': upcoming_registrants}

        elif 'clone training' in request.POST:
            # Fills form w/ initial details from cloned training,
            # Registrant has a chance to change things before proposing
            cloned = Training.objects.get(pk=request.POST['cloned_training_id'])
            initial_training = {}
            cloned_attrs = ['location_type', 'name', 'onsk8s', 'contact',
                    'description', 'skill', 'sessions'
                    ]
            for attr in cloned_attrs:
                initial_training[attr]=getattr(cloned, attr)

            formlist = [TrainingModelForm(initial=initial_training, user=user)]
            context_dict = {
                    'trainings_coached': trainings_coached,
                    'formlist': formlist,
                    'training_made': training_made,
                    'upcoming_registrants': upcoming_registrants
                    }

        else:  # If training_id not in post; if training is just being made.
            trainingmodelform = TrainingModelForm(request.POST,user=user)
            if trainingmodelform.is_valid():
                training_made = trainingmodelform.save()
                coach, c_create = Coach.objects.get_or_create(user=user)
                if c_create:
                    coach.save()
                training_made.coach.add(coach)
                training_made.save()

                if training_made:
                    if not training_made.onsk8s:
                        formlist = [DurationOnly()]

                    context_dict = {
                            'most_upcoming_con': most_upcoming_con,
                            'trainings_coached': trainings_coached,
                            'formlist': formlist,
                            'training_made': training_made,
                            'upcoming_registrants': upcoming_registrants
                            }
            else:  # If not valid
                add_fail = True
                context_dict = {
                        'add_fail': add_fail,
                        'training_made': training_made
                        }

    else:  # If not post
        context_dict = {
                'most_upcoming_con': most_upcoming_con,
                'trainings_coached': trainings_coached,
                'training_made': training_made,
                'upcoming_registrants': upcoming_registrants
                }
        if user.upcoming_cons():  # Otherwise will say "you don't have a pass.."
            context_dict['formlist'] = [TrainingModelForm(user=user)]

    # all end up here, regardless of post or not, or what's in post
    return render_to_response(
            'propose_new_training.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def register_training(request, o_id):
    """Adds registrants to trainingrosters for training occurrences.
    Permissions and timing checked in view.
    """

    user=request.user
    add_fail=None
    skater_added=None
    remove_fail= False
    skater_remove=None
    roster=None
    occur=None

    try:
        occur = Occurrence.objects.get(pk=int(o_id))
        training = occur.training
        Tos = list(Occurrence.objects.filter(training=training))
    except ObjectDoesNotExist:
        return render_to_response(
                'register_training.html',
                {},
                context_instance=RequestContext(request)
                )

    if occur and (user in occur.can_add_sk8ers()):

        registered, rc = TrainingRoster.objects.get_or_create(registered=occur)
        auditing, ac = TrainingRoster.objects.get_or_create(auditing=occur)

        # Make initial respectiv forms for each trainingroster
        roster_dict = {}
        for roster in [registered, auditing]:
            form_dict = {
                'search_form': SearchForm(),
                'add_form': EligibleRegistrantForm(
                        my_arg=Registrant.objects.eligible_sk8ers(roster)
                        ),
                'remove_form': EligibleRegistrantForm(
                        my_arg=roster.participants.all()
                        )
                }
            roster_dict[roster] = form_dict

        if request.method == "POST":
            if 'add register' in request.POST or 'add audit' in request.POST:
                if 'add register' in request.POST:
                    roster = registered
                else:
                    roster = auditing
                if roster.spacea():
                    try:
                        skater_added = Registrant.objects.get(
                                pk=request.POST['eligible_registrant']
                                )
                        roster.participants.add(skater_added)
                        roster.save()
                    except:
                        add_fail = Registrant.objects.get(
                                pk=request.POST['eligible_registrant']
                                )
                    # Update forms
                    form_dict = roster_dict.get(roster)
                    form_dict['remove_form'] = EligibleRegistrantForm(
                            my_arg=roster.participants.all()
                            )
                    form_dict['add_form'] = EligibleRegistrantForm(
                            my_arg=Registrant.objects.eligible_sk8ers(roster)
                            )
                else:
                    add_fail = Registrant.objects.get(
                            pk=request.POST['eligible_registrant']
                            )

            elif 'remove register' in request.POST or 'remove audit' in request.POST:
                if 'remove register' in request.POST:
                    roster = registered
                else:
                    roster = auditing
                if 'eligible_registrant' in request.POST and request.POST['eligible_registrant'] not in no_list:
                    try:
                        skater_remove = Registrant.objects.get(
                                pk=request.POST['eligible_registrant']
                                )
                        roster.participants.remove(skater_remove)
                        roster.save()
                    except:
                        remove_fail = True
                else:
                    remove_fail = True
                # Update forms
                form_dict = roster_dict.get(roster)
                form_dict['remove_form'] = EligibleRegistrantForm(
                        my_arg=roster.participants.all()
                        )
                form_dict['add_form'] = EligibleRegistrantForm(
                        my_arg=Registrant.objects.eligible_sk8ers(roster)
                        )

            elif 'search register' in request.POST or 'search audit' in request.POST:
                if 'search register' in request.POST:
                    roster = registered
                else:
                    roster = auditing

                search_form = SearchForm(request.POST)
                if 'search_q' in request.POST and request.POST['search_q'] not in no_list:
                    entry_query = search_form.get_query(['sk8name','last_name','first_name'])
                    found_entries = Registrant.objects.eligible_sk8ers(roster).filter(entry_query)
                else:
                    found_entries=Registrant.objects.eligible_sk8ers(roster)
                    form_dict = roster_dict.get(roster)
                # Update forms
                form_dict = roster_dict.get(roster)
                form_dict['search_form'] = search_form
                form_dict['add_form'] = EligibleRegistrantForm(my_arg=found_entries)


        #  Regardless of if POST or not
        formlist = []
        for r in [registered, auditing]:  # so r won't get confused with roster
            form_dict = roster_dict.get(r)
            if not r.spacea():
                add_form = form_dict.get("add_form")
                add_form.fields['eligible_registrant'].widget.attrs['disabled'] = True
                search_form = form_dict.get("search_form")
                search_form.fields['search_q'].widget.attrs['disabled'] = True
            formlist.append([
                    form_dict.get("search_form"),
                    form_dict.get("add_form"),
                    form_dict.get("remove_form")
                    ])
        register_forms = formlist[0]
        audit_forms = formlist[1]


    else:  # if not occur or not user in occur.can_add_sk8ers()
        register_forms = []
        audit_forms = []

    context_dict = {
            'occur': occur,
            'roster':roster,
            'skater_remove': skater_remove,
            'remove_fail': remove_fail,
            'skater_added': skater_added,
            'add_fail': add_fail,
            'audit_forms': audit_forms,
            'register_forms': register_forms,
            'training': training,
            'user': user
            }

    return render_to_response(
            'register_training.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def edit_training(request, activity_id):
    """Coaches and Boss Ladies can edit Training. Not NSOs or anyone else."""

    user = request.user
    save_attept = False
    save_success = False
    formlist = []

    try:
        training = Training.objects.get(pk=int(activity_id))
        editable_by = training.editable_by()
    except ObjectDoesNotExist:
        return render_to_response('edit_training.html',{},context_instance=RequestContext(request))

    if request.method == "POST":

        if 'confirm delete' in request.POST:
            training.coach.clear()
            training.delete()
            return redirect('/scheduler/my_trainings/')

        elif 'delete' in request.POST :
            return render_to_response(
                    'confirm_training_delete.html',
                    {'training':training},
                    context_instance=RequestContext(request)
                    )

        elif 'save training' in request.POST:
            save_attept = True
            form = TrainingModelForm(request.POST, instance=training,user=user)
            if form.is_valid():
                form.save()
                save_success = True
            if 'duration' in request.POST:  # If off skates, can choose duration
                training.duration = request.POST['duration']
                training.save()

    # Happens regardless of POST or not
    if user in editable_by:
        formlist = [TrainingModelForm(instance=training,user=user)]
        if not training.onsk8s:
            formlist.append(DurationOnly(initial={'duration':training.duration}))
    else:
        formlist = None

    context_dict = {
            'training': training,
            'save_attept': save_attept,
            'save_success': save_success,
            'formlist': formlist
            }

    return render_to_response(
            'edit_training.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
def challenges_home(request, con_id=None,):

    if con_id:
        try:
            con=Con.objects.get(pk=con_id)
        except ObjectDoesNotExist:
            con = Con.objects.most_upcoming()
    else:
        con = Con.objects.most_upcoming()

    scheduled = list(Occurrence.objects.filter(challenge__con=con))

    if len(scheduled) > 0 and con.sched_visible:
        date_dict = OrderedDict()
        for day in con.get_date_range():
            date_dict[day] = []

        for o in scheduled:
            temp_list = date_dict.get(o.start_time.date())
            temp_list.append(o)
            date_dict[o.start_time.date()] = list(temp_list)

        for v in date_dict.values():
            v.sort(key=lambda o: o.start_time)
    else:
        date_dict = None

    context_dict = {
            'con':con,
            'con_list': list(Con.objects.all()),
            'date_dict': date_dict
            }

    return render_to_response(
            'challenges_home.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def edit_roster(request, roster_id):
    """For NSOs and Boss Ladies, not captains. Only lets you add/remove
    skaters, only is sk8er is eligible by skil, gender, etc.
    Captains are meant to use edit_challenge.
    """

    try:
        roster = Roster.objects.get(pk=roster_id)
    except ObjectDoesNotExist:
        return render_to_response('edit_roster.html',{},context_instance=RequestContext(request))
    try:
        challenge = Challenge.objects.get(Q(roster1=roster) | Q(roster2=roster))
    except:
        challenge = None

    user=request.user
    add_fail = False
    skater_added = False
    skater_remove = False
    remove_fail = False
    add_fail_reason = None
    participating_in = []

    if request.method == "POST":
        if 'add skater' in request.POST:
            skater_added, add_fail, add_fail_reason = (
                    roster.add_sk8er_challenge(request.POST['eligible_registrant'])
                    )

        elif 'remove skater' in request.POST:
            skater_remove, remove_fail = (
                    roster.remove_sk8er_challenge(request.POST['eligible_registrant'])
                    )
    # Done after, to make sure ater add/remove, so is up to date
    participants = EligibleRegistrantForm(my_arg=roster.participants.all())
    participants.fields['eligible_registrant'].label = "Rostered Skaters"
    participating_in = challenge.participating_in()

    if request.method == "POST" and 'search skater' in request.POST:
        skater_search_form=SearchForm(request.POST or None)
        skater_search_form.fields['search_q'].label = "Skater Name"
        entry_query = skater_search_form.get_query(['sk8name','last_name','first_name'])
        if entry_query:
            found_entries = Registrant.objects.basic_eligible(roster).filter(entry_query)
            eligible_participants = EligibleRegistrantForm(my_arg=found_entries)
            eligible_participants.fields['eligible_registrant'].label = "Found Eligible Skaters"
        else:
            found_entries = Registrant.objects.basic_eligible(roster)
            eligible_participants = EligibleRegistrantForm(my_arg=found_entries)
            eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"

    else:  # not post or not searching for skater
        skater_search_form = SearchForm()
        skater_search_form.fields['search_q'].label = "Skater Name"
        found_entries = Registrant.objects.basic_eligible(roster)
        eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
        eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"

    context_dict = {'challenge': challenge, 'skater_search_form': skater_search_form,
            'participants': participants,'eligible_participants': eligible_participants,
            'add_fail_reason': add_fail_reason, 'add_fail': add_fail,
            'skater_added': skater_added, 'user': user, 'skater_remove': skater_remove,
            'remove_fail': remove_fail, 'roster': roster
            }

    return render_to_response(
            'edit_roster.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def edit_challenge(request, activity_id):
    user=request.user
    registrant_list = list(user.registrant_set.all())
    try:
        challenge=Challenge.objects.get(pk=int(activity_id))
        registrant=Registrant.objects.get(con=challenge.con, user=user)
        my_team,opponent,my_acceptance,opponent_acceptance=challenge.my_team_status([registrant])
    except ObjectDoesNotExist:
        challenge=None
        return render_to_response('edit_challenge.html',{},context_instance=RequestContext(request))

    opponent_form_list=None
    participants=None
    captain_replacements=None
    eligible_participants=None
    roster_form=None
    challenge_form=None
    add_fail=False
    add_fail_reason=False
    skater_added=False
    skater_remove=False
    remove_fail=False
    invited_captain=False
    problem_criteria=None
    potential_conflicts=None
    team_changes_made=False
    skater_search_form=None
    formlist=None
    coed_beginner = None
    captain_conflict=None
    save_attempt=False
    save_success=False
    entry_query=None

    if request.method == "POST":

        if 'confirm save' in request.POST or 'save team' in request.POST:

            save_attempt=True
            pre_save_gender=my_team.gender
            pre_save_skill=my_team.skill
            if challenge.gametype=="6GAME":
                roster_form=GameRosterCreateModelForm(request.POST, instance=my_team)
                challenge_form=GameModelForm(request.POST,user=user, instance=challenge)
                my_team=roster_form.save(commit=False)#without this, criteria conflict was running off old gender/skill.
            else:
                roster_form=ChallengeRosterModelForm(request.POST, user=user,instance=my_team)
                challenge_form=ChallengeModelForm(request.POST,user=user, instance=challenge)
                my_team=roster_form.save(commit=False)#without this, criteria conflict was running off old gender/skill.
            #don't save yet, just changing skill and gender for problem criteria check

            if 'save team' in request.POST:
                #don't save yet, just changing skill and gender for problem criteria check
                problem_criteria,potential_conflicts,captain_conflict=my_team.criteria_conflict()
                if captain_conflict:
                    pass

                elif problem_criteria or potential_conflicts:
                    this_reg=None#just a holdover so i can re use same html
                    return render_to_response('conflict_warning.html',{'roster':my_team,'activity_id':activity_id,'registrant':this_reg,'hidden_forms':[roster_form,challenge_form],'problem_criteria':problem_criteria,'potential_conflicts':potential_conflicts},context_instance=RequestContext(request))

            else:#if confirm save
                conflict_sweep=my_team.conflict_sweep()

            if not captain_conflict and roster_form.is_valid() and challenge_form.is_valid():
                #this should run regardless of save team or confirm save, assuming it doesn't jump to conflict warning
                #this is only if just updating team, not creating new or swapping captains or anything
                roster=roster_form.save()
                #I only want this to run for challenges. games are automatically any skill any gender.
                if not challenge.gametype=="6GAME":
                    coed_beginner =roster.coed_beginner()
                    if coed_beginner:
                        roster.save()
                challenge=challenge_form.save()
                roster.con=challenge.con
                roster.save()
                my_team=roster#keep this to get new saved data for my_team
                save_success=True
            else:
                #print "Captain conflict or Errors: ",roster_form.errors, challenge_form.errors
                #to prevent rejected unsaved changes form showing up in form
                if "gender" in problem_criteria:
                    my_team.gender=pre_save_gender
                if "skill" in problem_criteria:
                    my_team.skill=pre_save_skill

        elif 'add skater' in request.POST:
            skater_added,add_fail,add_fail_reason=my_team.add_sk8er_challenge(request.POST['eligible_registrant'])

        elif 'remove skater' in request.POST:
            skater_remove,remove_fail=my_team.remove_sk8er_challenge(request.POST['eligible_registrant'])

        elif 'invite captain' in request.POST or 'game_team' in request.POST:
            if 'invite captain' in request.POST:
                if request.POST['eligible_registrant'] not in ["None",None,"",u'']:
                    invited_captain=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                    if opponent:
                        if opponent.captain:
                            prev_cap=opponent.captain
                        else:
                            prev_cap=None
                        opponent.captain=invited_captain
                        opponent.save()#this is so captain save will reset captian number
                        if prev_cap:
                            prev_cap.save()#to reset captain #
                    else:#if this is the first time and there is no opponent
                         opponent=Roster(captain=invited_captain, con=invited_captain.con)
                         opponent.save()

                    opponent.defaults_match_captain()

            if my_team==challenge.roster1:
                challenge.roster2=opponent
            elif my_team==challenge.roster2:
                challenge.roster1=opponent

            challenge.save()
            if opponent:
                opponent.save()
                opponent.captain.save()#to get captaining number accurate

        elif 'search captains' in request.POST:
            captain_search_form=SearchForm(request.POST or None)
            captain_search_form.fields['search_q'].label = "Captain Name"
            entry_query = captain_search_form.get_query(['sk8name','last_name','first_name'])

        elif 'search skater' in request.POST:
            skater_search_form=SearchForm(request.POST or None)
            skater_search_form.fields['search_q'].label = "Skater Name"
            skater_entry_query = skater_search_form.get_query(['sk8name','last_name','first_name'])
            if skater_entry_query:
                found_entries = Registrant.objects.eligible_sk8ers(my_team).filter(skater_entry_query).order_by('sk8name','last_name','first_name')
                eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
                eligible_participants.fields['eligible_registrant'].label = "Found Eligible Skaters"
            else:
                found_entries = Registrant.objects.eligible_sk8ers(my_team).order_by('sk8name','last_name','first_name')
                eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
                eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"

        elif 'replace captain' in request.POST:
            swap_attempt=True
            try:
                new_captain=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                return render_to_response('captain_swap_confirm.html',{'swp_attempt':swap_attempt,'new_captain':new_captain,'roster':my_team,'activity_id':activity_id},context_instance=RequestContext(request))
            except:
                pass

        elif 'confirm captain replace' in request.POST:
            swap_attempt=True
            try:
                new_captain=Registrant.objects.get(pk=request.POST['new_captain'])
                old_captain=my_team.captain
                my_team.captain=new_captain
                new_captain.save()
                my_team.save()
                old_captain.save()#to reset captaining#
                swap_success=True
            except:
                swap_success=False

            return render_to_response('captain_swap_confirm.html',{'swap_attempt':swap_attempt,'new_captain':new_captain,'roster':my_team,'activity_id':activity_id},context_instance=RequestContext(request))

    #this line starts things that happen regardless of whether is request.post or not
    my_team,opponent,my_acceptance,opponent_acceptance=challenge.my_team_status([registrant])

    if my_team:
        if my_acceptance:
            if challenge.gametype=="6GAME":
                roster_form=GameRosterCreateModelForm(instance=my_team)
                challenge_form=GameModelForm(user=user,instance=challenge)

            else:
                roster_form=ChallengeRosterModelForm(user=user,instance=my_team)
                challenge_form=ChallengeModelForm(user=user,instance=challenge)
            formlist=[roster_form,challenge_form]
            ###############this part sloppy hack to keep searched skater name from showing up in both captain and skater search.
            if request.method == "POST" and 'search skater' in request.POST:
                skater_search_form=SearchForm(request.POST)
            else:
                skater_search_form=SearchForm()
            ##################################
            skater_search_form.fields['search_q'].label = "Skater Name"
            if request.method != "POST" or 'search skater' not in request.POST:
                eligible_participants=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(my_team))
                eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"
            participants=EligibleRegistrantForm(my_arg=my_team.participants.exclude(pk=my_team.captain.pk))
            participants.fields['eligible_registrant'].label = "Rostered Skaters"

            captain_replacements=EligibleRegistrantForm(my_arg=my_team.participants.filter(captaining__lt=MAX_CAPTAIN_LIMIT).exclude(pk=my_team.captain.pk ))
            captain_replacements.fields['eligible_registrant'].label = "Potential Captains"


            if not opponent or not opponent.captain or not opponent_acceptance:
                if entry_query:
                    #these used to be lists, but i don't think it matters. but if stops working, that's why
                    eligible_opponents = Registrant.objects.filter(entry_query).filter(con=challenge.con, pass_type__in=['MVP','Skater'], skill__in=['A','B','C']).exclude(pk=registrant.pk).order_by('sk8name','last_name','first_name')
                else:
                    eligible_opponents=Registrant.objects.filter(con=challenge.con,pass_type__in=['MVP','Skater'], skill__in=['A','B','C']).exclude(pk=registrant.pk)

                eligibleregistrantform=EligibleRegistrantForm(my_arg=eligible_opponents)
                if entry_query:
                    eligibleregistrantform.fields['eligible_registrant'].label = "Found Captains"
                else:
                    eligibleregistrantform.fields['eligible_registrant'].label = "All Eligible Captains"

                ###############this part sloppy hack to keep searched skater name from showing up in both captain and skater search.
                if request.method == "POST" and 'search captains' in request.POST:
                    captain_search_form=SearchForm(request.POST)
                else:
                    captain_search_form=SearchForm()
                ##################################

                captain_search_form.fields['search_q'].label = "Captain Name"
                opponent_form_list=[captain_search_form,eligibleregistrantform]

            formlist=[roster_form,challenge_form]

    big_dict={'problem_criteria':problem_criteria,'save_attempt':save_attempt,'save_success':save_success,'captain_conflict':captain_conflict,'coed_beginner':coed_beginner,'skater_search_form':skater_search_form,'invited_captain':invited_captain,'formlist':formlist,'eligible_participants':eligible_participants,'participants':participants,'captain_replacements':captain_replacements,'opponent_form_list':opponent_form_list,'my_team':my_team,'opponent':opponent,'challenge':challenge,
        'add_fail_reason':add_fail_reason,'add_fail':add_fail,'skater_added':skater_added,'skater_remove':skater_remove,'remove_fail':remove_fail,'opponent_acceptance':opponent_acceptance,'my_acceptance':my_acceptance}

    return render_to_response('edit_challenge.html',big_dict,context_instance=RequestContext(request))

#-------------------------------------------------------------------------------
@login_required
def challenge_respond(request):
    """Should always be post from Edit Challange, if not post, goes to index.
    takes in which challenge, who captain is, saves whether accepted or rejected,
    redrects to my challenges if rejected, edit challenge if accepted.
    """
    user = request.user
    if request.method == "POST":

        challenge = Challenge.objects.get(pk=request.POST['activity_id'])
        registrant = Registrant.objects.get(pk=request.POST['registrant_id'])
        my_team, opponent, my_acceptance, opponent_acceptance = (
                challenge.my_team_status([registrant])
                )

        if 'reject' in request.POST  or 'reject_confirm' in request.POST:
            if 'reject_confirm' in request.POST:
                # Has to be first to reject properly, otherwise is still accepted
                challenge.rosterreject(my_team)
                if challenge.pk:  # If challenge has not just been deleted
                    challenge.save()  # Necessary

                registrant.save()  # reset captain number
                return redirect('/scheduler/my_challenges/')
            else:  # If just 'reject' in post, need to confirm first
                context_dict = {
                        'opponent_acceptance': opponent_acceptance,
                        'my_team': my_team,
                        'challenge': challenge,
                        'opponent': opponent
                        }
                return render_to_response(
                        'confirm_challenge_reject.html',
                        context_dict,
                        context_instance=RequestContext(request)
                        )

        elif "accept" in request.POST:
            if 'clone_existing_team' in request.POST:
                team2mimic = Roster.objects.get(pk=request.POST['game_team'])
                my_team = team2mimic.clone_roster(recipient=my_team)
                registrant.save()#reset captain #

            elif 'create_new_team' in request.POST:
                my_team.gender = registrant.gender
                my_team.skill = registrant.skill + "O"
                my_team.name = None
                my_team.save()

            else:  # If just accepting, from edit challenge
                my_teams_as_cap = list(registrant.captain.exclude(name=None))
                if len(my_teams_as_cap) > 0:
                    form = MyRosterSelectForm(team_list=my_teams_as_cap)
                    if my_team in my_teams_as_cap:
                        form = MyRosterSelectForm(team_list=my_teams_as_cap)
                        form.fields["game_team"].initial = str(my_team.pk)
                    else:
                         form = MyRosterSelectForm(team_list=my_teams_as_cap)

                    context_dict = {
                            'form': form,
                            'opponent': opponent,
                            'my_team': my_team,
                            'challenge': challenge,
                            'registrant':registrant
                            }
                    return render_to_response(
                            'challenge_respond.html',
                            context_dict,
                            context_instance=RequestContext(request)
                            )

            # Could put this after initialy accept,
            # but wanted to wait until maybe give team a name first.
            if (challenge.roster1 and challenge.roster1.captain and
                    challenge.roster1.captain==registrant
                    ):
                challenge.captain1accepted=True
            elif (challenge.roster2 and challenge.roster2.captain and
                    challenge.roster2.captain==registrant
                    ):
                challenge.captain2accepted=True
            challenge.save()
            return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')

    else:  # Should never happen, should always be post
        return redirect('/')

#-------------------------------------------------------------------------------
def view_challenge(request, activity_id):
    """View Challenge detail. Various levels of permission for viewing and
    editing depending on if user is anonymous, skating in the challenge, an NSO,
    or a boss lady.
    """

    try:
        challenge = Challenge.objects.get(pk=int(activity_id))
        rosters = [challenge.roster1, challenge.roster2]
    except ObjectDoesNotExist:
        challenge = None
        rosters = None

    # Figure out what user is allowed to do and see
    user = request.user
    if user.is_authenticated():
        reg_list = user.registrants()
        if challenge:
            if user in challenge.editable_by() or user.can_edit_score():
                can_edit = True
            else:
                can_edit = False
            # user could have many registrants, any in participating in will do.
            cparts = set(challenge.participating_in())
            if len(cparts.intersection(reg_list)) > 0 or can_edit:
                # Roster participants and NSOs
                participating = True
            else:
                participating = False
    else:  # If AnonymousUser
        reg_list =[]
        can_edit = False
        participating = False

    score_form = None
    comm_form = None
    communication_saved = False

    if challenge:
        if participating:
            # Bosses & NSOs can edit score, challenge is editable by captains,
            # all registrants on roster participants are participating.
            # all of them can see communication, only NSO, Boss, captain, edit.
            if user.can_edit_score():
                if request.method == "POST" and "save_score" in request.POST:
                    score_form = ScoreFormDouble(
                            request.POST,
                            my_arg=challenge
                            )
                    if score_form.is_valid():
                        challenge.roster1score=request.POST['roster1_score']
                        challenge.roster2score=request.POST['roster2_score']
                        challenge.save()
                else:
                    score_form = ScoreFormDouble(my_arg=challenge)

            if can_edit:  # NSOs, Boss Ladies, or Captains can get excel
                if 'download_excel' in request.POST:
                    occur = Occurrence.objects.get(challenge=challenge)
                    wb, xlfilename = occur.excel_backup()
                    response = HttpResponse(
                            content_type='application/vnd.openxmlformats-\
                                    officedocument.spreadsheetml.sheet'
                                    )
                    response['Content-Disposition'] = (
                            'attachment; filename=%s' % (xlfilename)
                            )
                    wb.save(response)
                    return response

                # Still in if can edit
                if 'communication' in request.POST:
                    comm_form = CommunicationForm(request.POST)
                    if comm_form.is_valid():
                        challenge.communication = request.POST['communication']
                        challenge.save()
                        communication_saved = True
                else:
                    comm_form = CommunicationForm(
                            initial={'communication': challenge.communication}
                            )
            else:#if just a skater, not can_edit
                comm_form = CommunicationForm(
                        initial={'communication': challenge.communication}
                        )
                comm_form.fields['communication'].widget.attrs['readonly'] = True
                comm_form.fields['communication'].widget.attrs.update(
                        {'style' : 'background-color:white;'}
                        )

    context_dict = {
            'communication_saved': communication_saved,
            'participating': participating,
            'comm_form': comm_form,
            'reg_list': reg_list,
            'score_form': score_form,
            'can_edit': can_edit,
            'user': user,
            'challenge': challenge,
            'rosters': rosters
            }

    return render_to_response(
            'view_challenge.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def my_challenges(request):

    user = request.user
    registrant_list = list(user.registrant_set.all())
    registrant_dict_list=[]

    for registrant in registrant_list:

        my_rosters = list(registrant.roster_set.all())
        my_chals = list(Challenge.objects.filter(
                Q(roster1__in=my_rosters) |
                Q(roster2__in=my_rosters) |
                Q(roster1__captain=registrant) |
                Q(roster2__captain=registrant))
                )

        # See how many times captaining a challenge, games are excluded
        chals_cap = list(Challenge.objects.filter(
                Q(roster1__captain=registrant) |
                Q(roster2__captain=registrant))
                .exclude(gametype="6GAME")
                )
        if len(chals_cap) >= MAX_CAPTAIN_LIMIT:
            cap_exceeded = True
        else:
            cap_exceeded = False

        registrant_dict = {
                'my_chals': my_chals,
                'chals_submitted': [c for c in chals_cap if c.submitted_on],
                'cap_exceeded': cap_exceeded,
                'sub_full': Challenge.objects.submission_full(registrant.con),
                'can_sub_date': registrant.con.can_submit_chlg_by_date(),
                'con': registrant.con,
                'registrant':registrant
                }
        registrant_dict_list.append(registrant_dict)

    if len(registrant_list) > 0:
        active = registrant_list[0].con
    else:
        active = None

    context_dict = {
            'MAX_CAPTAIN_LIMIT': MAX_CAPTAIN_LIMIT,  # Imported at top of file
            'CLOSE_CHAL_SUB_AT': CLOSE_CHAL_SUB_AT,  # Imported at top of file
            'active': active,
            'registrant_list': registrant_list,
            'user': user,
            'registrant_dict_list': registrant_dict_list
            }

    return render_to_response(
            'my_challenges.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def propose_new_challenge(request):
    """If you have pass, lets you propose Challenge/Game.
    If Challenge, after asks you to choose gender/skill.
    If successful, redirects to edit challenge.
    """

    # If creation success, these 6 Nones/[] get replaced.
    # Don't want to repeat w/ every possible failure
    challenge = None
    challenge_id = None
    my_team = None
    roster_id = None
    formlist = []
    my_teams_as_cap = []

    user = request.user
    upcoming_registrants = user.upcoming_registrants()
    cansk8 = False
    if upcoming_registrants:
        for reg in upcoming_registrants:
            # if more than 1 registrant, only 1 of these needs to be true
            if reg.can_sk8():
                cansk8 = True

    if request.method == "POST":

        if 'gender' in request.POST or 'clone roster' in request.POST:
            if 'gender' in request.POST:
                my_team = Roster.objects.get(pk=int(request.POST["roster_id"]))
                challenge = Challenge.objects.get(pk=int(request.POST["challenge_id"]))

                gsf = GenderSkillForm(request.POST, captain=my_team.captain)
                if gsf.is_valid():
                    my_team.gender = request.POST["gender"]
                    my_team.skill = request.POST["skill"]
                    my_team.save()

            elif 'clone roster' in request.POST:
                old_team = Roster.objects.get(pk=request.POST['roster_to_clone_id'])
                my_team = old_team.clone_roster()
                challenge = Challenge(roster1=my_team,con=my_team.con)
                try:
                    old_chal = Challenge.objects.get(
                            Q(roster1=old_team) |
                            Q(roster2=old_team)
                            )
                    challenge.location_type = old_chal.location_type
                except:
                    location_type = "Flat Track"  # Easy default

            # Runs if either gender or clone is successful
            if my_team and challenge:
                challenge.save()
                my_team.captain.save()  # to adjust captaining number

        else: # If not cloning roster, not saving gender/skill, first make
            challenge_form = GameModelForm(request.POST or None, user=user)
            roster_form = GameRosterCreateModelForm(request.POST)
            if roster_form.is_valid() and challenge_form.is_valid():
                my_team=roster_form.save(commit=False)
                my_team.captain = Registrant.objects.get(
                        user=user, con__id=request.POST['con']
                        )
                my_team.con = my_team.captain.con
                my_team.save()
                my_team.save()  # To put self on roster
                challenge=challenge_form.save(commit=False)
                challenge.roster1 = my_team
                challenge.save()
                my_team.captain.save()  # To adjust captaining number

                if challenge.gametype != "6GAME":
                # Only need these 2 if need to specify gender/skill, or failure
                    roster_id = my_team.pk
                    challenge_id = challenge.pk
                    formlist = [GenderSkillForm(captain=my_team.captain)]

        # Regardless of whether cloned or made by post,
        # if new challenge has been born
        if challenge and my_team and not formlist:
            return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')

    # This is where not request.post starts
    elif cansk8:
        for r in upcoming_registrants:
            rosters = list(r.captain.exclude(name=None))
            my_teams_as_cap += list(rosters)

        formlist = [
                GameRosterCreateModelForm(request.POST or None),
                GameModelForm(request.POST or None, user=user)
                ]

    # Runs if not post, if posts and errors, or if need to get gender/skill
    context_dict = {
            'challenge_id': challenge_id,
            'roster_id': roster_id,
            'my_teams_as_cap': my_teams_as_cap,
            'cansk8': cansk8,
            'upcoming_registrants': upcoming_registrants,
            'formlist':formlist
            }

    return render_to_response(
            'propose_new_challenge.html',
            context_dict,
            context_instance=RequestContext(request)
            )

#-------------------------------------------------------------------------------
@login_required
def challenge_submit(request):
    """This should always be a post, from either my_challenges or maybe
    from edit_challenge. Will only accept within challenge submission window.
    """

    challenge = None
    is_captain = False
    submit_attempt = False
    can_submit_chlg = False
    unsubmit_attempt = False

    if request.method == "POST":  # should always be true
        challenge = Challenge.objects.get(pk=request.POST['activity_id'])
        user = request.user
        registrant_list = list(user.registrant_set.all())

        if (challenge.roster1 and challenge.roster1.captain and
                challenge.roster1.captain in registrant_list
                ):
            is_captain=True
        elif (challenge.roster2 and challenge.roster2.captain and
                challenge.roster2.captain in registrant_list
                ):
            is_captain=True

        if 'submit_challenge' in request.POST:
            submit_attempt = True
            can_submit_chlg = challenge.can_submit_chlg()
            if can_submit_chlg:
                challenge.submitted_on = timezone.now()
                challenge.save()
        elif 'confirm unsubmit' in request.POST:
            unsubmit_attempt = True
            if not challenge.con.schedule_final():
                challenge.submitted_on = None
                challenge.save()

        elif 'challenge unsubmit' in request.POST:
            unsubmit_attempt = True

    context_dict = {
            'unsubmit_attempt': unsubmit_attempt,
            'submit_attempt': submit_attempt,
            'can_submit_chlg': can_submit_chlg,
            'is_captain': is_captain,
            'challenge':challenge
            }

    return render_to_response(
            'challenge_submit.html',
            context_dict,
            context_instance=RequestContext(request)
            )


# @login_required
# def review_con(request,con_id):
#     user=request.user
#     con=Con.objects.get(pk=int(con_id))
#     try:
#         registrant=Registrant.objects.get(user=user, con=con)
#     except ObjectDoesNotExist:
#         registrant=None
#     save_attempt=False
#     save_success=False
#     myreview=None#needs to be here in case training and registrant exist, but reg wasn't signed up for training
#     form1=None
#     form2=None
#
#     if registrant:
#         #I didn't use get or create here so it wouldn't be saved and incorporated into stats if they changed their mind.
#         try:
#             myreview=ReviewCon.objects.get(registrant=registrant)
#         except:
#             myreview=ReviewCon()
#
#         form1=ReviewConForm(request.POST or None, instance=myreview)
#         form2=ReviewConFormOptional(request.POST or None, instance=myreview)
#         form3=ReviewConRankForm(request.POST or None, instance=myreview)
#
#         if request.method == "POST":
#             save_attempt=True
#             if form1.is_valid() and form2.is_valid() and form3.is_valid():
#                 myreview.registrant=registrant#in case is new
#                 myreview.save()
#                 save_success=True
#
#     return render_to_response('review_con.html',{"myreview":myreview,"save_attempt":save_attempt,"save_success":save_success,"form1":form1,"form2":form2,"form3":form3,"registrant":registrant,"con":con},context_instance=RequestContext(request))
#
# @login_required
# def review_training(request,training_id):
#     user=request.user
#     try:
#         training=Training.objects.get(pk=int(training_id))
#         try:
#             registrant=Registrant.objects.get(user=user, con=training.con)
#         except ObjectDoesNotExist:
#             registrant=None
#     except ObjectDoesNotExist:
#         training=None
#         registrant=None
#
#     save_attempt=False
#     save_success=False
#     myreview=None#needs to be here in case training and registrant exist, but reg wasn't signed up for training
#     form1=None
#     form2=None
#
#     if training and registrant:
#
#         #make sure registrant was actually IN training
#         trainings=registrant.get_trainings_attended()
#         if training in trainings:
#             #I didn't use get or create here so it wouldn't be saved and incorporated into stats if they changed their mind.
#             try:
#                 myreview=ReviewTraining.objects.get(training=training, registrant=registrant)
#             except:
#                 myreview=ReviewTraining()
#
#         form1=ReviewTrainingForm(request.POST or None, instance=myreview)
#         form2=ReviewTrainingFormOptional(request.POST or None, instance=myreview)
#         if request.method == "POST":
#             save_attempt=True
#             if form1.is_valid() and form2.is_valid():
#                 myreview.training=training #in case is new
#                 myreview.registrant=registrant#in case is new
#                 myreview.save()
#                 save_success=True
#
#     return render_to_response('review_training.html',{"myreview":myreview,"save_attempt":save_attempt,"save_success":save_success,"form1":form1,"form2":form2,"training":training,"registrant":registrant},context_instance=RequestContext(request))
#
# @login_required
# def my_reviews(request):
#     user=request.user
#     registrant_list= list(user.registrant_set.all())
#     today=datetime.date.today()
#
#     registrant_dict_list=[]
#
#     for registrant in registrant_list:
#         if today > registrant.con.end:
#             conpassed=True
#         else:
#             conpassed=False
#
#         trainings=registrant.get_trainings_attended()
#
#         registrant_dict={'con':registrant.con, 'registrant':registrant,'conpassed':conpassed,'trainings':trainings}
#         registrant_dict_list.append(registrant_dict)
#
#     if len(registrant_list)>1:
#         most_recent_reg=registrant_list[0]
#         active=most_recent_reg.con
#     else:
#         active=None
#
#     return render_to_response('my_reviews.html', {'active':active,'user':user,'registrant_dict_list':registrant_dict_list},context_instance=RequestContext(request))
#
