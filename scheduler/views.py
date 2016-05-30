#scheduler.views
from django.shortcuts import render,render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.db import connection as dbconnection
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
#print "dbc0:", len(dbconnection.queries)
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from scheduler.forms import CommunicationForm,MyRosterSelectForm,GameRosterCreateModelForm,GameModelForm,CoachProfileForm,SendEmail,ChallengeModelForm,ChallengeRosterModelForm,TrainingModelForm,DurationOnly, ScoreFormDouble
from con_event.forms import EligibleRegistrantForm,SearchForm
from con_event.models import Con, Registrant
from scheduler.models import Coach,Roster, Challenge, Training,DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION,DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION,GAMETYPE
from scheduler.app_settings import MAX_CAPTAIN_LIMIT,CLOSE_CHAL_SUB_AT
from django.forms.models import model_to_dict
from datetime import timedelta, date
import collections
from django.core.mail import EmailMessage, send_mail
from django.core.exceptions import ObjectDoesNotExist
from rcreg_project.settings import SECOND_CHOICE_EMAIL,SECOND_CHOICE_PW
from swingtime.models import Occurrence,TrainingRoster

import django_tables2 as tables
from django_tables2  import RequestConfig
from scheduler.tables import RosterTable
no_list=["",u'',None,"None"]
#syntx reference:
            #selection = request.POST.copy()
            #print "selection", selection
            #session_id = request.POST['session_id']
            #mvp_id_list= selection.getlist('mvpid')
            #print "selectiondict: ",selectiondict
            #selectiondict=dict(selection.lists())
@login_required
def my_schedule(request):
    """Used for Registrants to see My Schedule. If reg_id is provided and User is a boss, can also be hijacked ot see other people's schedules"""
    user=request.user
    most_upcoming=Con.objects.most_upcoming()
    registrant_dict_list=[]
    me_coach=None
    spoof_reg=None
    spoof_user=None
    spoof_error=False

    # if reg_id:
    #     print "REG ID is: ",reg_id
    #     try:
    #         reg=Registrant.objects.get(pk=reg_id)
    #         registrant_list=[reg]
    #         upcoming_registrants=[reg]
    #         reg_coach=reg.user.is_a_coach()
    #     except ObjectDoesNotExist:
    #         return render_to_response('my_schedule.html',{},context_instance=RequestContext(request))
        #ll the stuff that happens if this is a Boss spoofing, not perosn checking their own schedule
    if user.is_the_boss() and ("registrant" in request.GET or "user" in request.GET): #and is a boss

        if "user" in request.GET: #and is a boss
            try:
                spoof_user=User.objects.get(pk=request.GET['user'])
                registrant_list=list(spoof_user.registrant_set.all())
                upcoming_registrants=spoof_user.upcoming_registrants()
                reg_coach=spoof_user.is_a_coach()
            except ObjectDoesNotExist:
                spoof_error=True
                registrant_list= list(user.registrant_set.all())
                upcoming_registrants=user.upcoming_registrants()
                reg_coach=user.is_a_coach()
                #return render_to_response('my_schedule.html',{'spoof_error':True},context_instance=RequestContext(request))

        elif "registrant" in request.GET: #and is a boss
            try:
                spoof_reg=Registrant.objects.get(pk=request.GET['registrant'])
                registrant_list=[spoof_reg]
                upcoming_registrants=[spoof_reg]
                reg_coach=spoof_reg.user.is_a_coach()
            except ObjectDoesNotExist:
                spoof_error=True
                registrant_list= list(user.registrant_set.all())
                upcoming_registrants=user.upcoming_registrants()
                reg_coach=user.is_a_coach()
                #return render_to_response('my_schedule.html',{'spoof_error':True},context_instance=RequestContext(request))
    else:
        #if not a boss, will always return own my schedule
        registrant_list= list(user.registrant_set.all())
        upcoming_registrants=user.upcoming_registrants()
        reg_coach=user.is_a_coach()

    #happens whether is reg checking thier own scheudle or Boss spoofing it
    if not spoof_error:
        for registrant in registrant_list:
            ###############temporarily commenting out jsut ot be sure registrant model method get_occurrences() works
            # reg_os=[]
            #
            # if reg_coach:
            #     coach_trains=reg_coach.training_set.filter(con=registrant.con)
            #     for t in coach_trains:
            #         reg_os+=list(t.occurrence_set.all())
            #
            # reg_trains=list(registrant.trainingroster_set.all())
            # for tr in reg_trains:
            #     if tr.registered:
            #         reg_os+=tr.registered
            #     elif tr.auditing:
            #         reg_os+=tr.auditing
            #
            # reg_ros=list(registrant.roster_set.all())
            # chal=[]
            # for ros in reg_ros:
            #     chal+=list(ros.roster1.all())
            #     chal+=list(ros.roster2.all())
            #     for c in chal:
            #         for o in c.occurrence_set.all(): #othersise it gets added 2x
            #             if o not in reg_os:
            #                 reg_os.append(o)
            # reg_os.sort(key=lambda o: o.start_time)
            ###############temporarily commenting out jsut ot be sure registrant model method get_occurrences() works

            registrant_dict={'con':registrant.con, 'registrant':registrant, 'reg_os':registrant.get_occurrences()}
            registrant_dict_list.append(registrant_dict)

    if upcoming_registrants and len(upcoming_registrants)>1:
        active=Con.objects.most_upcoming()
    else:
        try:
            most_upcoming_reg=registrant_list[0]
            active=most_upcoming_reg.con
        except:
            active=None


    return render_to_response('my_schedule.html',{'spoof_error':spoof_error,'spoof_user':spoof_user,'spoof_reg':spoof_reg,'active':active,'registrant_dict_list':registrant_dict_list,'registrant_list':registrant_list}, context_instance=RequestContext(request))


###############


@login_required
def email_captain(request, roster_id):
    """This form will only show if captain has agreed to accept emails and has a user with an emial address"""
    user=request.user
    roster=Roster.objects.get(pk=roster_id)
    captain=roster.captain
    email_success=False

    if request.method == "POST":
        form=None
        message=request.POST['message']
        if roster.can_email and roster.captain.user and roster.captain.user.email:
            subject=captain.user.first_name+", "+user.first_name+" has sent you a message through the RollerTron site!"
            message_body = ''.join(["Message below. Please respond to "+user.email+", not to us.\n\n\n",message])
            email = EmailMessage(subject=subject, body=message_body, to=[captain.user.email], reply_to=[user.email])
            try:
                email.send(fail_silently=False)
                email_success=True
            except:
                try:
                    #note that send_mail does not include reply to
                    send_mail(subject, message_body, from_email=SECOND_CHOICE_EMAIL, recipient_list=[captain.user.email],
                        fail_silently=False,auth_user=SECOND_CHOICE_EMAIL,auth_password=SECOND_CHOICE_PW)
                    email_success=True
                except:
                    email_success=False
    else:
        form=SendEmail()

    return render_to_response('email_captain.html',{'email_success':email_success,'form':form,'roster':roster}, context_instance=RequestContext(request))


@login_required
def coach_profile(request):
    save_attempt=False
    save_success=False
    user=request.user
    try:
        coach=Coach.objects.get(user=user)
    except ObjectDoesNotExist:
        return render_to_response('coach_profile.html',{},context_instance=RequestContext(request))

    if request.method == 'POST':
        form=CoachProfileForm(request.POST,instance=coach)
        save_attempt=True
        if form.is_valid():
            form.save()
            save_success=True
        else:
            #i should prob put errors in template. don't think i have.
            form=CoachProfileForm(request.POST,instance=coach)
    else:
        form=CoachProfileForm(instance=coach)

    return render_to_response('coach_profile.html',{'coach':coach,'form':form,'save_attempt':save_attempt,'save_success':save_success,'user':user},context_instance=RequestContext(request))


@login_required
def email_coach(request, coach_id):
    """This assumes that coach has a user and an user email address.
    I think it's important coaches supply an email address, how can you rely on someone you can't get in touch with?"""
    user=request.user
    coach=Coach.objects.get(pk=coach_id)
    email_success=False

    if request.method == "POST":
        form=None
        message=request.POST['message']
        if coach.can_email:
            subject=coach.user.first_name+", "+user.first_name+" has sent you a message through the RollerTron site!"
            message_body = ''.join(["Message below. Please respond to "+user.email+", not to us.\n\n\n",message])
            email = EmailMessage(subject=subject, body=message_body, to=[coach.user.email], reply_to=[user.email])
            try:
                email.send(fail_silently=False)
                email_success=True
            except:
                try:
                 #note that send_mail does not include reply to
                    send_mail(subject, message_body, from_email=SECOND_CHOICE_EMAIL, recipient_list=[coach.user.email],
                        fail_silently=False,auth_user=SECOND_CHOICE_EMAIL,auth_password=SECOND_CHOICE_PW)
                    email_success=True
                except:
                    email_success=False
    else:
        form=SendEmail()

    return render_to_response('email_coach.html',{'email_success':email_success,'form':form,'coach':coach}, context_instance=RequestContext(request))


def view_coach(request, coach_id):
    try:
        coach=Coach.objects.get(pk=coach_id)
        return render_to_response('view_coach.html',{'coach':coach}, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('view_coach.html',{},context_instance=RequestContext(request))


def view_training(request, activity_id,o_id=None):
    user=request.user
    single=False
    visible=False
    occur=None
    rosters=[]
    try:
        training=Training.objects.get(pk=int(activity_id))
        if o_id:
            try:
                occur=Occurrence.objects.get(training=training, pk=int(o_id))
                if hasattr(occur, 'registered'):
                    rosters.append(occur.registered)
                else:
                    rosters.append(True)#so that the Registered/Auditing order in template will still work

                if hasattr(occur, 'auditing'):
                    rosters.append(occur.auditing)
                else:
                    rosters.append(True)#so that the Registered/Auditing order in template will still work
            except:
                pass
        Tos=list(Occurrence.objects.filter(training=training))

        if training.con.sched_visible:
            visible=True
            occurrences=list(Occurrence.objects.filter(training=training))
            if len(occurrences)==1:
                single=occurrences[0]
        else:
            occurrences=[]
        return render_to_response('view_training.html',{'occur':occur,'Tos':Tos,'single':single,'occurrences':occurrences,'visible':visible,'user':user, 'training':training, 'rosters':rosters}, context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        return render_to_response('view_training.html',{},context_instance=RequestContext(request))


def trainings_home(request,con_id=None,):
    user=request.user
    con_list= list(Con.objects.all())
    #con_dict_list=[]#this is from chllenges, do i need it here too?
    if not con_id:
        con=Con.objects.most_upcoming()
    else:
        con=Con.objects.get(pk=con_id)

    scheduled=list(Occurrence.objects.filter(training__con=con))

    if len(scheduled)>0 and con.sched_visible:
        date_dict=collections.OrderedDict()
        for day in con.get_date_range():
            date_dict[day]=[]

        for o in scheduled:
            temp_list=date_dict.get(o.start_time.date())
            temp_list.append(o)
            date_dict[o.start_time.date()]=list(temp_list)

        for v in date_dict.values():
            v.sort(key=lambda o: o.start_time)
    else:
        date_dict=None

    return render_to_response('trainings_home.html', {'con':con,'con_list':con_list,'user':user,'date_dict':date_dict},context_instance=RequestContext(request))


@login_required
#def register_training(request, activity_id,o_id=None):
def register_training(request,o_id):
    #to do:
    #if volunteer, check time before allowing register. Right now only checks editable by
    #this needs to be changed completely, as i change trianing/registered structure
    user=request.user
    add_fail=None
    skater_added=None
    remove_fail=None
    skater_remove=None
    roster=None
    occur=None
    try:
        occur=Occurrence.objects.get(pk=int(o_id))
        training=occur.training
        Tos=list(Occurrence.objects.filter(training=training))
    except ObjectDoesNotExist:
        return render_to_response('register_training.html',{},context_instance=RequestContext(request))


    if occur and user in occur.can_add_sk8ers():
        #TODO: check if volunteer, if so, check time of class. if boss, let do this any time.

        registered, rcreated=TrainingRoster.objects.get_or_create(registered=occur)
        auditing, acreated=TrainingRoster.objects.get_or_create(auditing=occur)

        reg_search_form=SearchForm()
        reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(registered))
        reg_remove_form=EligibleRegistrantForm(my_arg=registered.participants.all())
        aud_search_form=SearchForm()
        #aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
        aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(auditing))
        aud_remove_form=EligibleRegistrantForm(my_arg=auditing.participants.all())

        if request.method == "POST":
            selection = request.POST.copy()
            print "selection", selection
            if 'search register' in request.POST:
                reg_search_form=SearchForm(request.POST)
                if 'search_q' in request.POST and request.POST['search_q'] not in no_list:
                    entry_query = reg_search_form.get_query(['sk8name','last_name','first_name'])
                    found_entries = Registrant.objects.filter(entry_query).filter(con=training.con, skill__in=training.skills_allowed(),intl__in=registered.intls_allowed()).order_by('sk8name','last_name','first_name')
                else:
                    found_entries=Registrant.objects.eligible_sk8ers(registered)
                reg_add_form=EligibleRegistrantForm(my_arg=found_entries)

            elif 'add register' in request.POST:
                try:
                    roster=registered
                    if registered.spacea():
                        skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        registered.participants.add(skater_added)
                        registered.save()
                        reg_remove_form=EligibleRegistrantForm(my_arg=registered.participants.all())
                        reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(registered))
                    else:
                        add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                except:
                    add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])

            elif 'remove register' in request.POST:
                try:
                    roster=registered
                    if 'eligible_registrant' in request.POST and request.POST['eligible_registrant'] not in no_list:
                        skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        registered.participants.remove(skater_remove)
                        registered.save()
                    else:
                        remove_fail=True
                    reg_remove_form=EligibleRegistrantForm(my_arg=registered.participants.all())
                    reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(registered))
                except:
                    remove_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
            elif 'search audit' in request.POST:
                aud_search_form=SearchForm(request.POST)
                if 'search_q' in request.POST and request.POST['search_q'] not in no_list:
                    entry_query = aud_search_form.get_query(['sk8name','last_name','first_name'])
                    found_entries = Registrant.objects.filter(entry_query).filter(con=training.con).order_by('sk8name','last_name','first_name')
                else:
                    found_entries=Registrant.objects.eligible_sk8ers(auditing)
                aud_add_form=EligibleRegistrantForm(my_arg=found_entries)
            elif 'add audit' in request.POST:
                try:
                    roster=auditing
                    if auditing.spacea():
                        skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        auditing.participants.add(skater_added)
                        auditing.save()
                        aud_remove_form=EligibleRegistrantForm(my_arg=auditing.participants.all())
                        aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(auditing))
                    else:
                        add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                except:
                    add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
            elif 'remove audit' in request.POST:
                try:
                    roster=auditing
                    if 'eligible_registrant' in request.POST and request.POST['eligible_registrant'] not in no_list:
                        skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        auditing.participants.remove(skater_remove)
                        auditing.save()
                    else:
                        remove_fail=True
                    aud_remove_form=EligibleRegistrantForm(my_arg=auditing.participants.all())
                    aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(auditing))
                except:
                    remove_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])

        register_forms=[reg_search_form,reg_add_form,reg_remove_form]
        audit_forms=[aud_search_form,aud_add_form,aud_remove_form]

        if not registered.spacea():
            reg_add_form.fields['eligible_registrant'].widget.attrs['disabled'] = True
            reg_search_form.fields['search_q'].widget.attrs['disabled'] = True
        if not auditing.spacea():
            aud_add_form.fields['eligible_registrant'].widget.attrs['disabled'] = True
            aud_search_form.fields['search_q'].widget.attrs['disabled'] = True
    else:
        register_forms=[]
        audit_forms=[]

    return render_to_response('register_training.html', {'occur':occur,'roster':roster,'skater_remove':skater_remove,'remove_fail':remove_fail,'skater_added':skater_added,'add_fail':add_fail,'audit_forms':audit_forms,'register_forms':register_forms,'training':training,'user':user},context_instance=RequestContext(request))


@login_required
def my_trainings(request):
    user=request.user
    registrant_list= list(user.registrant_set.all())
    most_upcoming=Con.objects.most_upcoming()
    #should prob do prefetch/select related, bet would cut down on db hits?
    registrant_dict_list=[]
    coach=user.is_a_coach()

    for registrant in registrant_list:

        if coach:
            my_trains=coach.training_set.filter(con=registrant.con)
        else:
            my_trains=None
        #later I'll need to write logic/liks for giving feedback if you're not the coach.
        registrant_dict={'con':registrant.con, 'registrant':registrant, 'my_trains':my_trains}
        registrant_dict_list.append(registrant_dict)

    upcoming_registrants=user.upcoming_registrants()
    if upcoming_registrants and len(upcoming_registrants)>1:
        active=Con.objects.most_upcoming()
    else:
        try:
            most_upcoming_reg=registrant_list[0]
            active=most_upcoming_reg.con
        except:
            active=None

    return render_to_response('my_trainings.html', {'active':active,'user':user,'registrant_dict_list':registrant_dict_list},context_instance=RequestContext(request))


@login_required
def edit_training(request, activity_id):
    ###TODO: this has logic to allow Users to add coaches, but i removed function from template.
    #Awaiting final confirm from Ivanna before changing view
    user=request.user
    registrant_list = list(user.registrant_set.all())
    eligible_coaches=None
    coaches=None
    add_fail=False
    skater_added=False
    skater_remove=False
    training_changes_made=False
    formlist=[]
    eligible_coaches=None
    search_form=SearchForm()
    coach_users=[]

    try:
        training=Training.objects.get(pk=int(activity_id))
        editable_by=training.editable_by()
    except ObjectDoesNotExist:
        return render_to_response('edit_training.html',{},context_instance=RequestContext(request))

    if request.method == "POST":

        if 'delete' in request.POST or 'remove coach' in request.POST:
            if 'remove coach' in request.POST:
                if request.POST['eligible_registrant'] not in ["None",None,"",u'']:
                    skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])

            if 'delete' in request.POST or int( training.coach.count() ) == 1:
                return render_to_response('confirm_training_delete.html',{'skater_remove':skater_remove,'training':training},context_instance=RequestContext(request))
            else:
                #had to monkey patch this way bc coach is legacy, but registrants vary by the year
                if skater_remove:
                    coach, created=Coach.objects.get_or_create(user=skater_remove.user)
                    training.coach.remove(coach)
                    training.save()
                    coach.save()

        elif 'confirm delete' in request.POST:
            training.coach.clear()
            training.delete()
            return redirect('/scheduler/my_trainings/')

        elif 'add coach' in request.POST:
            if request.POST['eligible_registrant'] not in ["None",None,"",u'']:
                skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                coach, created=Coach.objects.get_or_create(user=skater_added.user)
                training.coach.add(coach)
                training.save()
                coach.save()

        elif 'save training' in request.POST:#save training details
            if 'duration' in request.POST:#if off skates, can choose duratio
                training.duration=request.POST['duration']
                training.save()
            formlist=[TrainingModelForm(request.POST, instance=training,user=user)]

            for form in formlist:#formlist used to have 2, when i separated skill and had it in the roster.
                if form.is_valid():#this should run regardless of save team or conriem save, assuming it doesn't jump to conflict warning
                    form.save()
                    save_success=True
                    training_changes_made=True
                else:
                    print "ERRORS: ",form.errors

    if user in editable_by:
        formlist=[TrainingModelForm(instance=training,user=user)]
    else:
        formlist=None

    if request.method == "POST" and 'search_q' in request.POST:
        search_form=SearchForm(request.POST)
        entry_query = search_form.get_query(['sk8name','last_name','first_name'])
        if entry_query:
            found_entries = Registrant.objects.filter(entry_query).filter(con=training.con).exclude(id__in=[o.id for o in registrant_list]).order_by('sk8name','last_name','first_name')
            eligible_coaches=EligibleRegistrantForm(my_arg=found_entries)
            eligible_coaches.fields['eligible_registrant'].label = "Found Skaters"
        else:
            eligible_coaches=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con).exclude(id__in=[o.id for o in registrant_list]))
            eligible_coaches.fields['eligible_registrant'].label = "All Skaters"
    else:
        eligible_coaches=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
        eligible_coaches.fields['eligible_registrant'].label = "All Skaters"

    coach_registrants=training.get_coach_registrants()
    coaches=EligibleRegistrantForm(my_arg=coach_registrants)
    for c in coach_registrants:
        coach_users.append(c.user)
    coaches.fields['eligible_registrant'].label = "Coaches"
    if formlist and not training.onsk8s:
        formlist.append(DurationOnly(initial={'duration':training.duration}))

    return render_to_response('edit_training.html',{'coach_users':coach_users,'search_form':search_form,'user':user,'editable_by':editable_by,'coaches':coaches,'eligible_coaches':eligible_coaches,'skater_remove':skater_remove,'add_fail':add_fail,'skater_added':skater_added,'training':training,'training_changes_made':training_changes_made,'formlist':formlist},context_instance=RequestContext(request))

@login_required
def propose_new_training(request):
    user=request.user
    upcoming_registrants=user.upcoming_registrants()
    conlist=user.upcoming_cons()
    trainings_coached=user.trainings_coached()
    add_fail=False
    training_made=False
    formlist=[]
    most_upcoming_con=Con.objects.most_upcoming()

    if request.method == "POST":
        #selection = request.POST.copy()
        #print "selection", selection

        if 'duration' in request.POST:
            training_made=Training.objects.get(pk=request.POST['training_id'])
            training_made.duration=request.POST['duration']
            training_made.save()

        elif 'clone training' in request.POST:
            cloned=Training.objects.get(pk=request.POST['cloned_training_id'])
            initial_training={'location_type':cloned.location_type,
                #need to change con
                'name':cloned.name,
                'onsk8s':cloned.onsk8s,
                'contact':cloned.contact,
                'description':cloned.description,
                'skill':cloned.skill,
                'sessions':cloned.sessions
                }
            formlist=[TrainingModelForm(initial=initial_training,user=user)]
            return render_to_response('propose_new_training.html', {'trainings_coached':trainings_coached,'formlist':formlist,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))

        else: #if training_id not in post, ie if training is just being made
            trainingmodelform=TrainingModelForm(request.POST,user=user)
            if trainingmodelform.is_valid():
                #NOTE TO SELF:
                #order: make training first so it can be connected to.
                #you need to commit false on registered because a roster with no connections,captain, or name will be deleted in a post save signal
                #then connect training to registered/auditing. then save all.
                training_made=trainingmodelform.save()
                ###########redo, or delete, or whatever###############
                # registered_made.con=training_made.con
                # registered_made.gender='NA/Coed'
                # auditing_made=Roster(gender='NA/Coed',skill=None,intl=False,con=training_made.con)
                # registered_made.registered=training_made
                # auditing_made.auditing=training_made
                # auditing_made.save()
                # registered_made.save()#then save to the relationship is kept.
                # auditing_made.save()
                #################redo, or delete, or whatever#########
                coach, c_create=Coach.objects.get_or_create(user=user)
                if c_create:
                    coach.save()
                training_made.coach.add(coach)
                training_made.save()

                if training_made and not training_made.onsk8s:
                    formlist=[DurationOnly()]
                    return render_to_response('propose_new_training.html', {'most_upcoming_con':most_upcoming_con,'trainings_coached':trainings_coached,'formlist':formlist,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))
            else:
                add_fail=True
                # print "errors"
                # if not trainingmodelform.is_valid():
                #     print "trainingmodelform.errors"
                #     print trainingmodelform.errors

        return render_to_response('new_training_made.html', {'add_fail':add_fail,'training_made':training_made},context_instance=RequestContext(request))

    else:
        if conlist:
            formlist=[TrainingModelForm(user=user)]

    return render_to_response('propose_new_training.html', {'most_upcoming_con':most_upcoming_con,'formlist':formlist,'trainings_coached':trainings_coached,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))


def challenges_home(request,con_id=None,):
    user=request.user
    con_list= list(Con.objects.all())
    con_dict_list=[]
    if not con_id:
        con=Con.objects.most_upcoming()
    else:
        con=Con.objects.get(pk=con_id)

    scheduled=list(Occurrence.objects.filter(challenge__con=con))

    if len(scheduled)>0 and con.sched_visible:
        date_dict=collections.OrderedDict()
        for day in con.get_date_range():
            date_dict[day]=[]

        for o in scheduled:
            temp_list=date_dict.get(o.start_time.date())
            temp_list.append(o)
            date_dict[o.start_time.date()]=list(temp_list)

        for v in date_dict.values():
            v.sort(key=lambda o: o.start_time)
    else:
        date_dict=None

    return render_to_response('challenges_home.html', {'user':user,'con':con,'con_list':con_list,'date_dict':date_dict},context_instance=RequestContext(request))


@login_required
def edit_roster(request, roster_id):
        #This is for NSOs and Boss Ladies, not captains. Captains are meant to use edit_challenge
        #right now only shows you eligible skaters. Should I let NSOs and boss ladies register anyone?
    user=request.user
    try:
        roster=Roster.objects.get(pk=roster_id)
    except ObjectDoesNotExist:
        return render_to_response('edit_roster.html',{},context_instance=RequestContext(request))

    #make sure this works with Game rosters tht can have several challenges attached to it
    try:
        challenge=Challenge.objects.get(Q(roster1=roster)|Q(roster2=roster))
    except:
        challenge=None

    add_fail=False
    skater_added=False
    skater_remove=False
    remove_fail=False

    if request.method == "POST":
        if 'add skater' in request.POST:
            skater_added,add_fail=roster.add_sk8er_challenge(request.POST['eligible_registrant'])

        elif 'remove skater' in request.POST:
            skater_remove,remove_fail=roster.remove_sk8er_challenge(request.POST['eligible_registrant'])

    participants=EligibleRegistrantForm(my_arg=roster.participants.all())
    participants.fields['eligible_registrant'].label = "Rostered Skaters"
    if request.method == "POST" and 'search skater' in request.POST:
        skater_search_form=SearchForm(request.POST or None)
        skater_search_form.fields['search_q'].label = "Skater Name"
        entry_query = skater_search_form.get_query(['sk8name','last_name','first_name'])
        if entry_query:
            found_entries = Registrant.objects.eligible_sk8ers(roster).filter(entry_query)
            eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
            eligible_participants.fields['eligible_registrant'].label = "Found Eligible Skaters"
        else:
            found_entries = Registrant.objects.eligible_sk8ers(roster).order_by('sk8name','last_name','first_name')
            eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
            eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"
    else:
        skater_search_form=SearchForm()
        skater_search_form.fields['search_q'].label = "Skater Name"
        eligible_participants=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(roster))
        eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"


    return render_to_response('edit_roster.html',{'challenge':challenge,'skater_search_form':skater_search_form,'participants':participants,'eligible_participants':eligible_participants,'add_fail':add_fail,'skater_added':skater_added,'user':user,
        'skater_remove':skater_remove,'remove_fail':remove_fail,'roster':roster}, context_instance=RequestContext(request))


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
            if challenge.is_a_game:
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
                if not challenge.is_a_game:#I only want this to run for challenges. games are automatically any skill any gender.
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
            skater_added,add_fail=my_team.add_sk8er_challenge(request.POST['eligible_registrant'])

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
            if challenge.is_a_game:
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
        'add_fail':add_fail,'skater_added':skater_added,'skater_remove':skater_remove,'remove_fail':remove_fail,'opponent_acceptance':opponent_acceptance,'my_acceptance':my_acceptance}

    return render_to_response('edit_challenge.html',big_dict,context_instance=RequestContext(request))

@login_required
def challenge_respond(request):
    '''This should always be post from Edit Challange, if not post jsut goes to index
    takes in which challenge, who captain is, saves whether accepted or rejected,
    redrects to my challenges if rejected, edit challenge if accepted'''
    user=request.user
    if request.method == "POST":

        challenge=Challenge.objects.get(pk=request.POST['activity_id'])
        registrant=Registrant.objects.get(pk=request.POST['registrant_id'])
        my_team,opponent,my_acceptance,opponent_acceptance=challenge.my_team_status([registrant])

        if 'reject' in request.POST  or 'reject_confirm' in request.POST:
            if 'reject_confirm' in request.POST:
                challenge.rosterreject(my_team)#has to be first to reject properly, otherwise is still accepted
                if challenge.pk:#if challenge has not just been deleted
                    challenge.save()#this is necessary

                registrant.save()#this is important to reset captain number
                return redirect('/scheduler/my_challenges/')
            else:#if just 'reject' in post, need to confirm first
                return render_to_response('confirm_challenge_reject.html',{'opponent_acceptance':opponent_acceptance,'my_team':my_team, 'challenge':challenge,'opponent':opponent}, context_instance=RequestContext(request))

        elif "accept" in request.POST:
            if 'clone_existing_team' in request.POST:
                ###I couldn't decide whether it would be better to clone a rostr and delete old one, or use existing roster to make just like one to be clones.
                #I decided to mimic, keeping in mind I'd hav to update if i ever change relevant attributes that need to be mimicked
                team2mimic=Roster.objects.get(pk=request.POST['game_team'])
                my_team.mimic_roster(team2mimic)

                if my_team.con!=registrant.con:#This is not necessary, I only look for teams this year. Didn't know that when I wrot eit, decided to keep it as safeguard in case i ever let it look at old teams as well.
                    my_team.participants.clear()
                    my_team.con=registrant.con
                    my_team.save()#captain should be added here

                registrant.save()#reset captian #

            elif 'create_new_team' in request.POST:
                skill_str=registrant.skill+"O"
                #I don't want these to run f game team
                my_team.gender=registrant.gender#to avoid weird save errors w/ eligibility
                my_team.skill=skill_str#to avoid weird save errors w/ eligibility
                my_team.name=None
                my_team.save()

            else:#if just accepting, from edit chal
                my_teams_as_cap=list(registrant.captain.exclude(name=None))
                if len(my_teams_as_cap)>0:
                    form=MyRosterSelectForm(team_list=my_teams_as_cap)
                    if my_team in my_teams_as_cap:
                        form=MyRosterSelectForm(team_list=my_teams_as_cap)
                        form.fields["game_team"].initial =str(my_team.pk)
                    else:
                         form=MyRosterSelectForm(team_list=my_teams_as_cap)

                    return render_to_response('challenge_respond.html',{'form':form,'opponent':opponent,'my_team':my_team, 'challenge':challenge,'registrant':registrant}, context_instance=RequestContext(request))

            #technically i could put this after i initialy accept, but wanted to wait until maybe give team a name.
            if challenge.roster1 and challenge.roster1.captain and challenge.roster1.captain==registrant:
                challenge.captain1accepted=True
            elif challenge.roster2 and challenge.roster2.captain and challenge.roster2.captain==registrant:
                challenge.captain2accepted=True
            challenge.save()
            return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')
    else:#this should never happen, should always be post
        return redirect('/')


def view_challenge(request, activity_id):
    participating=False
    can_edit=False
    score_form=None
    communication_form=None
    communication_saved=False
    user=request.user
    #r1data=[]
    #r2data=[]
    try:
        registrant_list=list(user.registrant_set.all())
    except:
        registrant_list=None

    try:
        challenge=Challenge.objects.get(pk=int(activity_id))
        rosters=[challenge.roster1, challenge.roster2]
    except ObjectDoesNotExist:
        challenge=None
        rosters=None

    if challenge and registrant_list:

        if len( set(challenge.participating_in()).intersection(registrant_list) ) > 0:
            participating=True

        if user.can_edit_score() or (user in challenge.editable_by()) or participating:
            #these are all the people that can see communication
            if not request.method == "POST":
                communication_form=CommunicationForm(initial={'communication':challenge.communication})

            if user.can_edit_score() or (user in challenge.editable_by()):
                can_edit=True
                if request.method == "POST" and 'communication' in request.POST:
                    communication_form=CommunicationForm(request.POST)
                    if communication_form.is_valid():
                        challenge.communication=request.POST['communication']
                        challenge.save()
                        communication_saved=True
            else:#if just a skater
                communication_form.fields['communication'].widget.attrs['readonly'] = True
                communication_form.fields['communication'].widget.attrs.update({'style' : 'background-color:white;'})

        if user.can_edit_score():
            score_form=ScoreFormDouble(request.POST or None,my_arg=challenge)
            if request.method == "POST" and score_form.is_valid():
                if 'roster1_score' in request.POST and (request.POST['roster1_score'] not in [u'',"",None,"None"]):
                    challenge.roster1score=request.POST['roster1_score']
                if 'roster2_score' in request.POST and (request.POST['roster2_score'] not in [u'',"",None,"None"]):
                    challenge.roster2score=request.POST['roster2_score']
                challenge.save()
            else:
                print "not post or errors: ",score_form.errors
    #I was toying w/ letting sort name and # in this view, but I don't like the way it treats litte and capital like different letters,
    #And I can't highlight number dupes
    # if challenge and challenge.roster1:
    #     for s in challenge.roster1.participants.all():
    #         r1data.append({"sk8name":s.sk8name, "sk8number":s.sk8number})
    # if challenge and challenge.roster2:
    #     for s in challenge.roster2.participants.all():
    #         r2data.append({"sk8name":s.sk8name, "sk8number":s.sk8number})
    # print "r2data",r2data
    #
    # r1table = RosterTable(r1data)
    # RequestConfig(request).configure(r1table)
    #
    # r2table = RosterTable(r2data)
    # RequestConfig(request).configure(r2table)
    # tables=[r1table,r2table]

    return render_to_response('view_challenge.html',{"communication_saved":communication_saved,"can_edit":can_edit,'participating':participating,'communication_form':communication_form,'registrant_list':registrant_list,'score_form':score_form,'user':user,'challenge':challenge,'rosters':rosters}, context_instance=RequestContext(request))



@login_required
def my_challenges(request):
    user=request.user
    registrant_list= list(user.registrant_set.all())
    most_upcoming=Con.objects.most_upcoming()
    #should prob do prefetch/select related, bet would cut down on db hits?
    registrant_dict_list=[]

    for registrant in registrant_list:
        # pending=list(registrant.pending_challenges())
        # scheduled=registrant.scheduled_challenges()
        # unconfirmed=registrant.unconfirmed_challenges()
        pending=None
        scheduled=None
        unconfirmed=None

        my_rosters=list(registrant.roster_set.all())
        my_chals=list(Challenge.objects.filter(Q(roster1__in=my_rosters)|Q(roster2__in=my_rosters)|Q(roster1__captain=registrant)|Q(roster2__captain=registrant)))

        can_sub_date=registrant.con.can_submit_chlg_by_date()
        sub_full=Challenge.objects.submission_full(registrant.con)
        #see how many times captaining a challenge, games are excluded
        chals_cap=list(Challenge.objects.filter(Q(roster1__captain=registrant)|Q(roster2__captain=registrant)).exclude(is_a_game=True))
        if len(chals_cap)>=MAX_CAPTAIN_LIMIT:
            cap_exceeded=True
        else:
            cap_exceeded=False
        chals_submitted=[c for c in chals_cap if c.submitted_on]

        registrant_dict={'my_chals':my_chals,'chals_submitted':chals_submitted,'cap_exceeded':cap_exceeded,'sub_full':sub_full,'can_sub_date':can_sub_date,'con':registrant.con, 'registrant':registrant, 'scheduled':scheduled,'pending':pending,'unconfirmed':unconfirmed}
        registrant_dict_list.append(registrant_dict)

    upcoming_registrants=user.upcoming_registrants()
    if upcoming_registrants and len(upcoming_registrants)>1:
        active=Con.objects.most_upcoming()
    else:
        try:
            most_upcoming_reg=registrant_list[0]
            active=most_upcoming_reg.con
        except:
            active=None

    return render_to_response('my_challenges.html', {'MAX_CAPTAIN_LIMIT':MAX_CAPTAIN_LIMIT,'CLOSE_CHAL_SUB_AT':CLOSE_CHAL_SUB_AT,'active':active,'registrant_list':registrant_list,'user':user,'registrant_dict_list':registrant_dict_list},context_instance=RequestContext(request))

@login_required
def propose_new_game(request):
    """propose_new_game and propose_new_challenge are mostly the same, with mild differences sorted out in propose_new_activity"""
    return propose_new_activity(request,is_a_game=True)

@login_required
def propose_new_challenge(request):
    return propose_new_activity(request)


@login_required
def propose_new_activity(request,is_a_game=False):
    #reminder: challenge.is_a_game and is_a_game both exist. is_a_game exists for when the chalenge hasn't been made yet, to know user intention.
    user=request.user
    cansk8=False
    cancaptain=False
    formlist=None
    coed_beginner=None
    my_teams_as_cap=None
    captain_conflict=None
    problem_criteria=None
    my_team=None
    challenge=None
    roster_form=None

    upcoming_registrants=user.upcoming_registrants()
    if upcoming_registrants:
        for reg in upcoming_registrants:
            #if more than 1 registrant, only 1 of these needs to be true
            if reg.can_sk8():
                cansk8=True
            if reg.can_captain() or is_a_game:
                cancaptain=True

        if request.method == "POST":

            if 'is_a_game' in request.POST:
                is_a_game=True
                challenge_form=GameModelForm(request.POST or None,user=user)
            else:
                challenge_form=ChallengeModelForm(request.POST or None,user=user)

            #where i figure out or make my team
            if 'clone roster' in request.POST:
                old_team=Roster.objects.get(pk=request.POST['roster_to_clone_id'])
                my_team=old_team.clone_roster()
                if is_a_game:
                    roster_form=GameRosterCreateModelForm(instance=my_team)
                else:
                    roster_form=ChallengeRosterModelForm(user=user,instance=my_team)
                challenge=Challenge(roster1=my_team,con=my_team.con)
                challenge.save()
                my_team.captain.save()#to adjust captaining number

            else:
                if is_a_game:
                    roster_form=GameRosterCreateModelForm(request.POST)
                else:
                    roster_form=ChallengeRosterModelForm(request.POST,user=user)

                if roster_form.is_valid():
                    my_team=roster_form.save(commit=False)
                    try:
                        my_team.captain=Registrant.objects.get(user=user, con__id=request.POST['con'])
                        my_team.con=my_team.captain.con
                        problem_criteria,potential_conflicts,captain_conflict=my_team.criteria_conflict()
                    except:
                        pass#if can't get registrant

                    if my_team and not captain_conflict and challenge_form.is_valid():
                        my_team.save()
                        my_team.save()#put self on roster
                        challenge=challenge_form.save(commit=False)
                        challenge.roster1=my_team
                        challenge.captain1accepted=True
                        formlist=[]
                        if is_a_game:
                            coed_beginner=False
                            challenge.is_a_game=True
                        else:
                            coed_beginner=my_team.coed_beginner()

                        challenge.save()
                        my_team.captain.save()#to adjust captaining number
                    else:
                        if captain_conflict:
                            print "captain conflict"
                        if not challenge_form.is_valid():
                            print "challenge_form not valid"
                            print challenge_form.errors
                else:
                    print "roster form errors"
                    print roster_form.errors


            #regardless of whether cloned or made by post, if bew challenge has been born
            if challenge and my_team and not captain_conflict:
                return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')

        #this is where not request.post starts
        if cansk8:
            formlist=[]
            my_teams_as_cap=[]
            for r in upcoming_registrants:
                #my_teams_as_cap+=list(r.captain.exclude(name=None))
                rosters=list(Roster.objects.filter(captain=r))
                for r in rosters:#I don't know why i ahve to do it this way. .exclude name=None ecludes all, for osme reason
                    if not r.name:
                        rosters.remove(r)
                my_teams_as_cap+=list(rosters)

            if is_a_game:
                if not roster_form:
                    roster_form=GameRosterCreateModelForm(request.POST or None)
                formlist=[roster_form,GameModelForm(request.POST or None,user=user)]
            elif cancaptain:#I'm not sure why tis has request post but challenge does not...?
                if not roster_form:
                    roster_form=ChallengeRosterModelForm(user=user)
                formlist=[roster_form,ChallengeModelForm(request.POST or None,user=user)]

    return render_to_response('propose_new_challenge.html', {'problem_criteria':problem_criteria,'captain_conflict':captain_conflict,'my_teams_as_cap':my_teams_as_cap,'is_a_game':is_a_game,'cancaptain':cancaptain,'cansk8':cansk8,'upcoming_registrants':upcoming_registrants,'MAX_CAPTAIN_LIMIT':MAX_CAPTAIN_LIMIT,'formlist':formlist},context_instance=RequestContext(request))

@login_required
def challenge_submit(request):
    """This should always be a post, from either my_challenges or maybe edit_challenge.
    and will only accept within challenge submission window"""
    challenge=None
    is_captain=False
    submit_attempt=False
    can_submit_chlg=False
    unsubmit_attempt=False

    if request.method == "POST":
        challenge=Challenge.objects.get(pk=request.POST['activity_id'])
        user=request.user
        registrant_list= list(user.registrant_set.all())

        if challenge.roster1 and challenge.roster1.captain and challenge.roster1.captain in registrant_list:
            is_captain=True
        elif challenge.roster2 and challenge.roster2.captain and challenge.roster2.captain in registrant_list:
            is_captain=True

        if 'submit_challenge' in request.POST:
            submit_attempt=True
            can_submit_chlg=challenge.can_submit_chlg()
            if can_submit_chlg:
                challenge.submitted_on=timezone.now()
                challenge.save()
        #word order intentionally non-parallel to avoid confusion, having submit count as part of unsubmit
        elif 'confirm unsubmit' in request.POST:
            unsubmit_attempt=True
            if not challenge.con.schedule_final():
                challenge.submitted_on=None
                challenge.save()

        elif 'challenge unsubmit' in request.POST:
            unsubmit_attempt=True

    return render_to_response('challenge_submit.html', {'unsubmit_attempt':unsubmit_attempt,'submit_attempt':submit_attempt,'can_submit_chlg':can_submit_chlg,'is_captain':is_captain,'challenge':challenge},context_instance=RequestContext(request))
