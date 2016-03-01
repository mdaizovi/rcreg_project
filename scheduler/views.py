#scheduler.views
from django.shortcuts import render,render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.db import connection as dbconnection
from django.db.models import Q
from django.utils import timezone
#print "dbc0:", len(dbconnection.queries)
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from scheduler.forms import MyRosterSelectForm,GameRosterCreateModelForm,GameModelForm,CoachProfileForm,SendEmail,ChallengeModelForm,ChallengeRosterModelForm,TrainingRegisteredModelForm,TrainingModelForm,DurationOnly, ScoreFormDouble
from con_event.forms import EligibleRegistrantForm,SearchForm
from con_event.models import Con, Registrant
from scheduler.models import Coach,Roster, Challenge, Training,DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION,DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION,GAMETYPE
from scheduler.app_settings import MAX_CAPTAIN_LIMIT
from django.forms.models import model_to_dict
from datetime import timedelta, date
import collections
from django.core.mail import EmailMessage, send_mail
from rcreg_project.settings import CUSTOM_SITE_ADMIN_EMAIL, SECOND_CHOICE_EMAIL,SECOND_CHOICE_PW


#syntx reference:
            #selection = request.POST.copy()
            #print "selection", selection
            #session_id = request.POST['session_id']
            #mvp_id_list= selection.getlist('mvpid')
            #print "selectiondict: ",selectiondict
            #selectiondict=dict(selection.lists())

@login_required
def email_captain(request, roster_id):
    user=request.user
    roster=Roster.objects.get(pk=roster_id)
    captain=roster.captain
    email_success=False

    if request.method == "POST":
        form=None
        message=request.POST['message']
        if roster.can_email:
            subject=captain.user.first_name+", "+user.first_name+" has sent you a message through the RollerCon site!"
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
    coach=Coach.objects.get(user=user)

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
    user=request.user
    coach=Coach.objects.get(pk=coach_id)
    email_success=False

    if request.method == "POST":
        form=None
        message=request.POST['message']
        if coach.can_email:
            subject=coach.user.first_name+", "+user.first_name+" has sent you a message through the RollerCon site!"
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
    coach=Coach.objects.get(pk=coach_id)
    return render_to_response('view_coach.html',{'coach':coach}, context_instance=RequestContext(request))


def view_training(request, activity_id):
    user=request.user
    training=Training.objects.get(pk=int(activity_id))
    rosters=[training.registered, training.auditing]
    return render_to_response('view_training.html',{'user':user, 'training':training, 'rosters':rosters}, context_instance=RequestContext(request))


def trainings_home(request,con_id=None,):
    user=request.user
    con_list= list(Con.objects.all())
    if not con_id:
        con=Con.objects.most_upcoming()
    else:
        con=Con.objects.get(pk=con_id)

    scheduled=list(Training.objects.filter(con=con))

    if len(scheduled)>0:
        share=int(len(scheduled)/5) #hard coding for now because this is just for display

        day = con.start
        delta = timedelta(days=1)
        iter_no=0
        date_dict=collections.OrderedDict()#https://pymotw.com/2/collections/ordereddict.html
        while day <= con.end:
            this_share=scheduled[(share*iter_no):(share*(iter_no+1))]
            date_dict[day]=this_share
            day += delta
            iter_no+=1
    else:
        date_dict=None

    return render_to_response('trainings_home.html', {'con':con,'con_list':con_list,'user':user,'date_dict':date_dict},context_instance=RequestContext(request))


@login_required
def register_training(request, activity_id):
    #to do:
    #if volunteer, check time before allowing register. Right now only checks editable by

    user=request.user
    training=Training.objects.get(pk=int(activity_id))
    auditing, created=Roster.objects.get_or_create(con=training.con, auditing=training)
    add_fail=None
    skater_added=None
    remove_fail=None
    skater_remove=None
    roster=None

    if user in training.registered.editable_by():
        #TODO: check if volunteer, if so, check time of class. if boss, let do this any time.
        reg_search_form=SearchForm()
        reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(training.registered))
        reg_remove_form=EligibleRegistrantForm(my_arg=training.registered.participants.all())
        aud_search_form=SearchForm()
        aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
        aud_remove_form=EligibleRegistrantForm(my_arg=training.auditing.participants.all())

        if request.method == "POST":
            if 'search register' in request.POST:
                reg_search_form=SearchForm(request.POST)
                entry_query = reg_search_form.get_query(['sk8name','last_name','first_name'])
                found_entries = Registrant.objects.filter(entry_query).filter(con=training.con, gender__in=training.registered.genders_allowed(),skill__in=training.registered.skills_allowed(),intl__in=training.registered.intls_allowed()).order_by('sk8name','last_name','first_name')
                reg_add_form=EligibleRegistrantForm(my_arg=found_entries)

            elif 'add register' in request.POST:
                try:
                    roster=training.registered
                    if training.registered.spacea():
                        skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        training.registered.participants.add(skater_added)
                        training.registered.save()
                        reg_remove_form=EligibleRegistrantForm(my_arg=training.registered.participants.all())
                        reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(training.registered))
                    else:
                        add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                except:
                    add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])

            elif 'remove register' in request.POST:
                try:
                    roster=training.registered
                    skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                    training.registered.participants.remove(skater_remove)
                    training.registered.save()
                    reg_remove_form=EligibleRegistrantForm(my_arg=training.registered.participants.all())
                    reg_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(training.registered))
                except:
                    remove_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
            elif 'search audit' in request.POST:
                aud_search_form=SearchForm(request.POST)
                entry_query = aud_search_form.get_query(['sk8name','last_name','first_name'])
                found_entries = Registrant.objects.filter(entry_query).filter(con=training.con).order_by('sk8name','last_name','first_name')
                aud_add_form=EligibleRegistrantForm(my_arg=found_entries)
            elif 'add audit' in request.POST:
                try:
                    roster=training.auditing
                    if training.auditing.cap and training.auditing.spacea():
                        skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                        training.auditing.participants.add(skater_added)
                        training.auditing.save()
                        aud_remove_form=EligibleRegistrantForm(my_arg=training.auditing.participants.all())
                        aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
                    else:
                        add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                except:
                    add_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])
            elif 'remove audit' in request.POST:
                try:
                    roster=training.auditing
                    skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                    training.auditing.participants.remove(skater_remove)
                    training.auditing.save()
                    aud_remove_form=EligibleRegistrantForm(my_arg=training.auditing.participants.all())
                    aud_add_form=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
                except:
                    remove_fail=Registrant.objects.get(pk=request.POST['eligible_registrant'])

        register_forms=[reg_search_form,reg_add_form,reg_remove_form]
        audit_forms=[aud_search_form,aud_add_form,aud_remove_form]

        if not training.registered.spacea():
            reg_add_form.fields['eligible_registrant'].widget.attrs['disabled'] = True
            reg_search_form.fields['search_q'].widget.attrs['disabled'] = True
        if not training.auditing.spacea():
            aud_add_form.fields['eligible_registrant'].widget.attrs['disabled'] = True
            aud_search_form.fields['search_q'].widget.attrs['disabled'] = True
    else:
        register_forms=[]
        audit_forms=[]

    return render_to_response('register_training.html', {'roster':roster,'skater_remove':skater_remove,'remove_fail':remove_fail,'skater_added':skater_added,'add_fail':add_fail,'audit_forms':audit_forms,'register_forms':register_forms,'training':training,'user':user},context_instance=RequestContext(request))


@login_required
def my_trainings(request):
    user=request.user
    registrant_list= list(user.registrant_set.all())
    most_upcoming=Con.objects.most_upcoming()
    #should prob do prefetch/select related, bet would cut down on db hits?
    registrant_dict_list=[]
    coach=user.is_a_coach()

    for registrant in registrant_list:

        scheduled=registrant.scheduled_trainings()
        if coach:
            unconfirmed=coach.training_set.filter(con=registrant.con)
        else:
            unconfirmed=None
        #later I'll need to write logic/liks for giving feedback if you're not the coach.
        registrant_dict={'con':registrant.con, 'registrant':registrant, 'scheduled':scheduled,'unconfirmed':unconfirmed}
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
    user=request.user
    training=Training.objects.get(pk=int(activity_id))
    editable_by=training.editable_by()
    eligible_coaches=None
    coaches=None
    add_fail=False
    skater_added=False
    skater_remove=False
    training_changes_made=False
    formlist=[]
    eligible_coaches=None
    search_form=SearchForm()


    if request.method == "POST":

        if 'delete' in request.POST or 'remove coach' in request.POST:
            if 'remove coach' in request.POST:
                skater_remove=Registrant.objects.get(pk=request.POST['eligible_registrant'])

            if 'delete' in request.POST or int( training.coach.count() ) == 1:
                return render_to_response('confirm_training_delete.html',{'skater_remove':skater_remove,'training':training},context_instance=RequestContext(request))
            else:
                #had to monkey patch this way bc coach is legacy, but registrants vary by the year
                coach, created=Coach.objects.get_or_create(user=skater_remove.user)
                training.coach.remove(coach)
                training.save()
                coach.save()

        elif 'confirm delete' in request.POST:
            training.coach.clear()
            training.delete()
            return redirect('/scheduler/my_trainings/')

        elif 'add coach' in request.POST:
            skater_added=Registrant.objects.get(pk=request.POST['eligible_registrant'])
            coach, created=Coach.objects.get_or_create(user=skater_added.user)
            training.coach.add(coach)
            training.save()
            coach.save()

        elif 'save training' in request.POST:#save training details
            if 'duration' in request.POST:#if off skates, can choose duratio
                training.duration=request.POST['duration']
                training.save()
            formlist=[TrainingRegisteredModelForm(request.POST, instance=training.registered),TrainingModelForm(request.POST, instance=training,user=user)]

            for form in formlist:
                if form.is_valid():#this should run regardless of save team or conriem save, assuming it doesn't jump to conflict warning
                    form.save()
                    save_success=True
                    training_changes_made=True
                else:
                    print "ERRORS: ",form.errors

    if user in editable_by:
        formlist=[TrainingRegisteredModelForm(instance=training.registered),TrainingModelForm(instance=training,user=user)]
    else:
        formlist=None

    if request.method == "POST" and 'search_q' in request.POST:
        search_form=SearchForm(request.POST)
        entry_query = search_form.get_query(['sk8name','last_name','first_name'])
        found_entries = Registrant.objects.filter(entry_query).filter(con=training.con).order_by('sk8name','last_name','first_name')
        eligible_coaches=EligibleRegistrantForm(my_arg=found_entries)
        eligible_coaches.fields['eligible_registrant'].label = "Found Skaters"
    else:
        eligible_coaches=EligibleRegistrantForm(my_arg=Registrant.objects.filter(con=training.con))
        eligible_coaches.fields['eligible_registrant'].label = "All Skaters"


    coaches=EligibleRegistrantForm(my_arg=training.get_coach_registrants())
    coaches.fields['eligible_registrant'].label = "Coaches"
    if formlist and not training.onsk8s:
        formlist.append(DurationOnly(initial={'duration':training.duration}))

    return render_to_response('edit_training.html',{'search_form':search_form,'user':user,'editable_by':editable_by,'coaches':coaches,'eligible_coaches':eligible_coaches,'skater_remove':skater_remove,'add_fail':add_fail,'skater_added':skater_added,'training':training,'training_changes_made':training_changes_made,'formlist':formlist},context_instance=RequestContext(request))

@login_required
def propose_new_training(request):
    user=request.user
    upcoming_registrants=user.upcoming_registrants()
    conlist=user.upcoming_cons()
    trainings_coached=user.trainings_coached()
    add_fail=False
    training_made=False
    formlist=[]

    if request.method == "POST":

        if 'duration' in request.POST:
            training_made=Training.objects.get(pk=request.POST['training_id'])
            training_made.duration=request.POST['duration']
            training_made.save()

        elif 'clone training' in request.POST:
            cloned=Training.objects.get(pk=request.POST['cloned_training_id'])
            initial_training={'location_type':cloned.location_type,
                'name':cloned.name,
                'onsk8s':cloned.onsk8s,
                'contact':cloned.contact,
                'description':cloned.description,
                }
            initial_registered={'skill':cloned.registered.skill,'gender':cloned.registered.gender}
            formlist=[TrainingRegisteredModelForm(initial=initial_registered),TrainingModelForm(initial=initial_training,user=user)]
            return render_to_response('propose_new_training.html', {'trainings_coached':trainings_coached,'formlist':formlist,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))

        else: #if training_id not in post, ie if training is just being made
            trainingmodelform=TrainingModelForm(request.POST,user=user)
            trainingregisteredmodelform=TrainingRegisteredModelForm(request.POST)
            if trainingmodelform.is_valid() and trainingregisteredmodelform.is_valid():
                #NOTE TO SELF:
                #order: make training first so it can be connected to.
                #you need to commit false on registered because a roster with no connections,captain, or name will be deleted in a post save signal
                #then connect training to registered/auditing. then save all.
                training_made=trainingmodelform.save()
                registered_made=trainingregisteredmodelform.save(commit=False)#so delete homeless roster signal won't get called
                registered_made.con=training_made.con
                registered_made.gender='NA/Coed'
                auditing_made=Roster(gender='NA/Coed',skill='0',intl=False,con=training_made.con)
                registered_made.registered=training_made
                auditing_made.auditing=training_made
                auditing_made.save()
                registered_made.save()#then save to the relationship is kept.
                auditing_made.save()
                coach, c_create=Coach.objects.get_or_create(user=user)
                if c_create:
                    coach.save()
                training_made.coach.add(coach)
                training_made.save()

                if training_made and not training_made.onsk8s:
                    formlist=[DurationOnly()]
                    return render_to_response('propose_new_training.html', {'trainings_coached':trainings_coached,'formlist':formlist,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))
            else:
                add_fail=True

        return render_to_response('new_training_made.html', {'add_fail':add_fail,'training_made':training_made},context_instance=RequestContext(request))

    else:
        if conlist:
            formlist=[TrainingRegisteredModelForm(),TrainingModelForm(user=user)]

    return render_to_response('propose_new_training.html', {'formlist':formlist,'trainings_coached':trainings_coached,'training_made':training_made,'upcoming_registrants':upcoming_registrants},context_instance=RequestContext(request))


def challenges_home(request,con_id=None,):
    user=request.user
    con_list= list(Con.objects.all())
    con_dict_list=[]
    if not con_id:
        con=Con.objects.most_upcoming()
    else:
        con=Con.objects.get(pk=con_id)
    scheduled=list(Challenge.objects.filter(con=con, RCaccepted=True))

    if len(scheduled)>0:
        #hard coding for now because this is just for display
        day = con.start
        delta = timedelta(days=1)
        iter_no=0
        date_dict=collections.OrderedDict()#https://pymotw.com/2/collections/ordereddict.html
        while day <= con.end:
            date_dict[day]=scheduled
            day += delta
    else:
        date_dict=None

    return render_to_response('challenges_home.html', {'user':user,'con':con,'con_list':con_list,'date_dict':date_dict},context_instance=RequestContext(request))


@login_required
def edit_roster(request, roster_id):
        #This is for NSOs and Boss Ladies, not captains. Captains are meant to use edit_challenge
        #right now only shows you eligible skaters. Should I let NSOs and boss ladies register anyone?
    user=request.user
    roster=Roster.objects.get(pk=roster_id)

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
        found_entries = Registrant.objects.eligible_sk8ers(roster).filter(entry_query)
        eligible_participants=EligibleRegistrantForm(my_arg=found_entries)
        eligible_participants.fields['eligible_registrant'].label = "Found Eligible Skaters"
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
    challenge=Challenge.objects.get(pk=int(activity_id))
    registrant=Registrant.objects.get(con=challenge.con, user=user)
    my_team,opponent,my_acceptance,opponent_acceptance=challenge.my_team_status([registrant])

    registrant_list = list(user.registrant_set.all())
    opponent_form_list=None
    participants=None
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
    game_teams_form=None

    if request.method == "POST":
        if 'confirm save' in request.POST or 'save team' in request.POST:

#################I'm having problems with people trying to save existing teams as same name as other existing teams
                #so I need to get their existing team and swap them out, if exist.
            existing_team=None
            if 'name' in request.POST:
                my_team_name=ascii_only_no_punct(request.POST['name'])
                try:
                    existing_team=Roster.objects.get(con=registrant.con,captain=registrant, name=my_team_name)
                    old_team,selected_team=challenge.replace_team(my_team,existing_team)
                    my_team=selected_team
                except:
                    pass #if it still thows dupe entry errors I'll know this didn't work.
########################################

            save_attempt=True
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

            if not captain_conflict and roster_form.is_valid() and challenge_form.is_valid():#this should run regardless of save team or conriem save, assuming it doesn't jump to conflict warning
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
                print "Captain conflict or Errors: ",roster_form.errors, challenge_form.errors

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

            elif 'game_team' in request.POST:
                opponent=Roster.objects.get(pk=request.POST['game_team'])
                invited_captain=opponent.captain

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

    #this line starts things that happen regard;ess of whether is request.post or not
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

            skater_search_form=SearchForm()
            skater_search_form.fields['search_q'].label = "Skater Name"
            if request.method != "POST" or 'search skater' not in request.POST:
                eligible_participants=EligibleRegistrantForm(my_arg=Registrant.objects.eligible_sk8ers(my_team))
                eligible_participants.fields['eligible_registrant'].label = "All Eligible Skaters"
            participants=EligibleRegistrantForm(my_arg=my_team.participants.exclude(pk=my_team.captain.pk))
            participants.fields['eligible_registrant'].label = "Rostered Skaters"


            if not opponent or not opponent.captain or not opponent_acceptance:
                if entry_query:
                    if challenge.is_a_game:
                        eligible_opponents = Registrant.objects.filter(entry_query).filter(con=challenge.con, pass_type__in=['MVP','Skater'], skill__in=['A','B','C']).exclude(pk=registrant.pk).order_by('sk8name','last_name','first_name')
                    else:
                        eligible_opponents = Registrant.objects.filter(entry_query).filter(con=challenge.con, pass_type__in=['MVP','Skater'], skill__in=['A','B','C'],captaining__lt=MAX_CAPTAIN_LIMIT).exclude(pk=registrant.pk).order_by('sk8name','last_name','first_name')
                else:
                    if challenge.is_a_game:
                        eligible_opponents=list(Registrant.objects.filter(con=challenge.con,pass_type__in=['MVP','Skater'], skill__in=['A','B','C']).exclude(pk=registrant.pk))
                    else:
                        eligible_opponents=list(Registrant.objects.filter(con=challenge.con,pass_type__in=['MVP','Skater'], skill__in=['A','B','C'],captaining__lt=MAX_CAPTAIN_LIMIT).exclude(pk=registrant.pk))

                eligibleregistrantform=EligibleRegistrantForm(my_arg=eligible_opponents)
                if entry_query:
                    eligibleregistrantform.fields['eligible_registrant'].label = "Found Captains"
                else:
                    eligibleregistrantform.fields['eligible_registrant'].label = "All Eligible Captains"

                captain_search_form=SearchForm(request.POST or None)
                captain_search_form.fields['search_q'].label = "Captain Name"
                opponent_form_list=[captain_search_form,eligibleregistrantform]

                if challenge.is_a_game:
                    existing_games=Challenge.objects.filter(con=challenge.con,is_a_game=True)
                    game_teams=[]
                    for game in existing_games:
                        if game.roster1 and game.roster1.captain and game.roster1.captain != registrant and game.roster1.name and game.roster1 not in game_teams:
                            game_teams.append(game.roster1)
                        if game.roster2 and game.roster2.captain and game.roster2.captain != registrant and game.roster2.name and game.roster2 not in game_teams:
                            game_teams.append(game.roster2)

                    if len(game_teams)>0:
                        game_teams_form=MyRosterSelectForm(team_list=game_teams)

            formlist=[roster_form,challenge_form]

    big_dict={'game_teams_form':game_teams_form,'problem_criteria':problem_criteria,'save_attempt':save_attempt,'save_success':save_success,'captain_conflict':captain_conflict,'coed_beginner':coed_beginner,'skater_search_form':skater_search_form,'invited_captain':invited_captain,'formlist':formlist,'eligible_participants':eligible_participants,'participants':participants,'opponent_form_list':opponent_form_list,'my_team':my_team,'opponent':opponent,'challenge':challenge,
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
        if 'reject' in request.POST  or 'reject remain captain' in request.POST or 'reject leave team' in request.POST:
            if 'reject remain captain' in request.POST or 'reject leave team' in request.POST:
                challenge.rosterreject(my_team)#has to be first to reject properly, oterwise is still accepted
                old_team,selected_team=challenge.replace_team(my_team,None)#this is necessary, otherwise it won't save challenge
                challenge.rosterreject(my_team)#to delete homeless challenge
                if challenge.pk:#if challenge has not just been deleted
                    challenge.save()#this is necessary, otherwise it won't save challenge

                if 'reject leave team' in request.POST:
                    old_chal_set=list(my_team.roster1.all())+list(my_team.roster2.all())
                    for c in old_chal_set:
                        c.rosterreject(my_team)
                        old_team,selected_team=c.replace_team(my_team,None)
                        if c.pk:
                            c.save()
                    try:#because it's 1am and maybe i'm wrong # think this is redundant actually.
                        if my_team and my_team.participants.all() and registrant in my_team.participants.all():
                            my_team.participants.remove(registrant)
                    except:
                        pass
                    my_team.delete()

                registrant.save()#this is important to reset captain number
                return redirect('/scheduler/my_challenges/')
            else:
                return render_to_response('confirm_challenge_reject.html',{'opponent_acceptance':opponent_acceptance,'my_team':my_team, 'challenge':challenge,'opponent':opponent}, context_instance=RequestContext(request))

        elif "accept" in request.POST:
            if 'select_existing_team' in request.POST:
                selected_team=Roster.objects.get(pk=request.POST['game_team'])
                my_old_team,my_team=challenge.replace_team(my_team,selected_team)
                if my_old_team and my_old_team!= selected_team:
                    if my_old_team.captain and my_old_team.captain == registrant:#( can probably do this in method, but unsure if I'll always want
                        print "this is probably where all the none teams are coming form, views line 769"
                        my_old_team.captain=None
                        try:#because it's 1am and maybe i'm wrong # think this is redundant actually.
                            if my_old_team and my_old_team.participants.all() and registrant in my_old_team.participants.all():
                                my_old_team.participants.remove(registrant)
                        except:
                            pass

                        try:#because it's 1am and maybe i'm wrong # think this is redundant actually.
                            if not my_old_team.name and not my_old_team.captain and my_old_team.is_homeless:
                                my_old_team.delete()
                            else:
                                my_old_team.save()
                        except:
                            try:
                                my_old_team.save()
                            except:
                                pass #i really need to check this when it's not 2am

                        registrant.save()#reset captian #
            else:
                skill_str=registrant.skill+"O"
                if 'create_new_team' in request.POST:
                    pass #i jsut want to use old team, but save gender etc below
                else:
                    my_teams_as_cap=list(registrant.captain.exclude(name=None))
                    if len(my_teams_as_cap)>0:
                        form=MyRosterSelectForm(team_list=my_teams_as_cap)
                        if my_team in my_teams_as_cap:
                            form=MyRosterSelectForm(team_list=my_teams_as_cap)
                            form.fields["game_team"].initial =str(my_team.pk)
                        else:
                             form=MyRosterSelectForm(team_list=my_teams_as_cap)

                        return render_to_response('challenge_respond.html',{'form':form,'opponent':opponent,'my_team':my_team, 'challenge':challenge,'registrant':registrant}, context_instance=RequestContext(request))
                #I don't want these to run f game team
                my_team.gender=registrant.gender#to avoid weird save errors w/ eligibility
                my_team.skill=skill_str#to avoid weird save errors w/ eligibility
                my_team.name=None
                my_team.save()


            #is a game but want new team, or if a game but no other teams, or if not  game. all accept.
            if challenge.roster1 and challenge.roster1.captain and challenge.roster1.captain==registrant:
                challenge.captain1accepted=True
            elif challenge.roster2 and challenge.roster2.captain and challenge.roster2.captain==registrant:
                challenge.captain2accepted=True
            challenge.save()


            return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')
    else:#this should never happen, should always be post
        return redirect('/')


def view_challenge(request, activity_id):
    user=request.user
    try:
        registrant_list=list(user.registrant_set.all())
    except:
        registrant_list=None
    challenge=Challenge.objects.get(pk=int(activity_id))
    rosters=[challenge.roster1, challenge.roster2]

    if registrant_list and user.can_edit_score():
        if request.method == "POST":
            form=ScoreFormDouble(request.POST, my_arg=challenge)
            if form.is_valid():
                roster1_score = request.POST['roster1_score']
                roster2_score = request.POST['roster2_score']
                challenge.roster1score=roster1_score
                challenge.roster2score=roster2_score
                challenge.save()
            else:
                print "errors: ",form.errors

        score_form=ScoreFormDouble(my_arg=challenge)
    else:
        score_form=None

    return render_to_response('view_challenge.html',{'registrant_list':registrant_list,'score_form':score_form,'user':user,'challenge':challenge,'rosters':rosters}, context_instance=RequestContext(request))



@login_required
def my_challenges(request):
    user=request.user
    registrant_list= list(user.registrant_set.all())
    most_upcoming=Con.objects.most_upcoming()
    #should prob do prefetch/select related, bet would cut down on db hits?
    registrant_dict_list=[]

    for registrant in registrant_list:
        pending=list(registrant.pending_challenges())
        scheduled=registrant.scheduled_challenges()
        unconfirmed=registrant.unconfirmed_challenges()
        registrant_dict={'con':registrant.con, 'registrant':registrant, 'scheduled':scheduled,'pending':pending,'unconfirmed':unconfirmed}
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

    return render_to_response('my_challenges.html', {'active':active,'registrant_list':registrant_list,'user':user,'registrant_dict_list':registrant_dict_list},context_instance=RequestContext(request))

@login_required
def propose_new_game(request):
    """propose_new_game and propose_new_challenge are mostly the same, with mild differences sorted out in propose_new_activity"""
    return propose_new_activity(request,is_a_game=True)
@login_required
def propose_new_game_new_team(request):
    """propose_new_game and propose_new_challenge are mostly the same, with mild differences sorted out in propose_new_activity"""
    return propose_new_activity(request,is_a_game=True,create_new_team=True)
@login_required
def propose_new_challenge(request):
    return propose_new_activity(request)
@login_required
def propose_new_challenge_new_team(request):
    """propose_new_challenge but with creating a new team instead of looking for your old ones"""
    return propose_new_activity(request,is_a_game=False,create_new_team=True)



@login_required
def propose_new_activity(request,is_a_game=False,create_new_team=False):
    #reminder: challenge.is_a_game and is_a_game both exist. is_a_game exists for when the chalenge hasn't been made yet, to know user intention.
    user=request.user
    cansk8=False
    cancaptain=False
    registrant=None
    formlist=None
    coed_beginner=None
    my_teams_as_cap=None
    game_teams_form=None
    captain_conflict=None
    problem_criteria=None
    opposing_roster=None
    challenged_captain=None
    IntegrityErrorMSG=None

    upcoming_registrants=user.upcoming_registrants()
    if upcoming_registrants:
        for reg in upcoming_registrants:
            #if more than 1 registrant, only 1 of these needs to be true
            if reg.can_sk8():
                cansk8=True
            if reg.can_captain() or is_a_game:
                cancaptain=True

        if request.method == "POST":
            challenged_captain=None
            my_team=None
            if 'is_a_game' in request.POST:
                is_a_game=True

            if 'challenge_id' in request.POST:
                challenge=Challenge.objects.get(pk=request.POST['challenge_id'])
            else:
                challenge=False

            if 'con' in request.POST:#somehow I'm gonna find out the fucking con
                con=Con.objects.get(pk=request.POST['con'])
            elif challenge:
                con=challenge.con
            elif challenged_captain:
                con=challenged_captain.con

            if 'eligible_registrant' in request.POST and (request.POST['eligible_registrant'] not in ['None',None]):#if selected a captain to challenge
                eligibleregistrantform=EligibleRegistrantForm(request.POST, my_arg=None)
                if eligibleregistrantform.is_valid():
                    challenged_captain=Registrant.objects.get(pk=request.POST['eligible_registrant'])
                    #if not select existing opposing game team, this us okay for either
                    #need to make new roster skill and gender suit captain, otherwise when they try to save profile they get a confusing conflict sweep message
                    skill_str=challenged_captain.skill+"O"#this will make default team skill either AO,BO,or CO
                    opposing_roster=Roster(captain=challenged_captain, con=challenged_captain.con, gender=challenged_captain.gender, skill=skill_str)
                    opposing_roster.save()
                    opposing_roster.save()#again, to add cap to roster
                    challenge.roster2=opposing_roster
                    challenge.save()
                    formlist=None
                    opposing_roster.save()#needs to happen twice to add captain to roster, so will show up in their my challenges
                    challenged_captain.save()#to adjust captaining number
                else:
                    print "Errors: "

            elif 'challenge team' in request.POST:#if made a game and selected opponent from existing game teams
                opposing_roster=Roster.objects.get(pk=request.POST['game_team'])
                challenge.roster2=opposing_roster
                challenge.save()
                challenged_captain=opposing_roster.captain
                formlist=None

            else:#if  eligible registrant not in post, ie if challenge is just being made
                try:
                    registrant=Registrant.objects.get(user=user, con__id=request.POST['con'])
                    if is_a_game:
                        challenge_form=GameModelForm(request.POST,user=user)
                    else:
                        challenge_form=ChallengeModelForm(request.POST,user=user)
                except:
                    pass

                #where i figure out or make my team
                if 'game_team' in request.POST or 'my_team'in request.POST or 'name' in request.POST:
                    if 'game_team' in request.POST:
                        my_team=Roster.objects.get(pk=request.POST['game_team'])
                        roster_form=None
                    elif 'my_team'in request.POST:
                        my_team=Roster.objects.get(pk=request.POST['my_team'])
                    elif 'name' in request.POST:
                        if request.POST['name'] not in [None,"None","",u'']:
                            my_team_name=ascii_only_no_punct(request.POST['name'])
                            try:
                                my_team=Roster.objects.get(con=con,captain=registrant, name=my_team_name)
                            except:
                                my_team=Roster(con=con,captain=registrant, name=my_team_name)
                        else:
                            my_team=Roster(con=con,captain=registrant)

                if is_a_game:
                    roster_form=GameRosterCreateModelForm(request.POST, instance=my_team)
                else:
                    roster_form=ChallengeRosterModelForm(request.POST,user=user,instance=my_team)

                if registrant and cancaptain:#so this should be true if is_a_game, bc of top of view
                    if not my_team and roster_form:
                        if roster_form.is_valid():#HERE's where I los emy rost                        print "my_team before roster form sacv",my_team
                            my_team=roster_form.save(commit=False)
                            problem_criteria,potential_conflicts,captain_conflict=my_team.criteria_conflict()

                    if not captain_conflict and challenge_form.is_valid():
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
                            if coed_beginner:
                                my_team.save()

                        challenge.save()
                        registrant.save()#to adjust captaining number

            if not challenged_captain or not opposing_roster:#I don't need to see these forms if they just invited someone

                if is_a_game:
                    if challenge:#I'm not sure how this is running w/out kniwing the challenge,i got errors about challenge being a bool,
                    #so trying to supply con otherwise just in case.
                        existing_games=Challenge.objects.filter(con=challenge.con,is_a_game=True)
                    else:
                        existing_games=Challenge.objects.filter(con=con,is_a_game=True)
                    game_teams=[]
                    for game in existing_games:
                        if game.roster1 and game.roster1.captain and game.roster1.captain not in upcoming_registrants and game.roster1.name and game.roster1 not in game_teams:
                            game_teams.append(game.roster1)
                        if game.roster2 and game.roster2.captain and game.roster2.captain not in upcoming_registrants and game.roster2.name and game.roster2 not in game_teams:
                            game_teams.append(game.roster2)

                    if len(game_teams)>0:
                        game_teams_form=MyRosterSelectForm(team_list=game_teams)
                    else:
                        game_teams_form=None

                search_form=SearchForm(request.POST or None)
                entry_query=None
                if 'search_q' in request.POST:
                    my_team=Roster.objects.get(pk=request.POST['my_team'])
                    entry_query = search_form.get_query(['sk8name','last_name','first_name'])
                if entry_query:
                    if challenge and challenge.is_a_game:#if is a game, max captain limit doesn't matter
                        captains = Registrant.objects.filter(entry_query).filter(con=challenge.con, pass_type__in=['MVP','Skater'],skill__in=['A','B','C']).exclude(id__in=[o.id for o in upcoming_registrants]).order_by('sk8name','last_name','first_name')
                    else:
                        captains = Registrant.objects.filter(entry_query).filter(con=con, pass_type__in=['MVP','Skater'],skill__in=['A','B','C'], captaining__lt=MAX_CAPTAIN_LIMIT).exclude(id__in=[o.id for o in upcoming_registrants]).order_by('sk8name','last_name','first_name')
                else:#if no search querty or search fail
                    if challenge and challenge.is_a_game:
                        captains=Registrant.objects.filter(con=challenge.con, pass_type__in=['MVP','Skater'],skill__in=['A','B','C']).exclude(id__in=[o.id for o in upcoming_registrants])
                    else:
                        captains=Registrant.objects.filter(con=con, pass_type__in=['MVP','Skater'], skill__in=['A','B','C'], captaining__lt=MAX_CAPTAIN_LIMIT).exclude(id__in=[o.id for o in upcoming_registrants])

                eligibleregistrantform=EligibleRegistrantForm(my_arg=captains)
                formlist=[search_form,eligibleregistrantform]

            if challenge and (my_team or opposing_roster) and not captain_conflict:
                return redirect('/scheduler/challenge/edit/'+str(challenge.id)+'/')

        #this is where not request.post starts
        if not challenged_captain or not opposing_roster:#I don't need to see these forms if they just invited someone
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
                if len(my_teams_as_cap)>0 and not create_new_team:
                    if is_a_game or cancaptain:
                        formlist=[MyRosterSelectForm(team_list=my_teams_as_cap)]
                else:
                    if is_a_game:
                        formlist=[GameRosterCreateModelForm(request.POST or None)]
                    elif cancaptain:
                        formlist=[ChallengeRosterModelForm(user=user)]
                    my_teams_as_cap=None
                if is_a_game:
                    formlist+=[GameModelForm(request.POST or None,user=user)]
                else:
                    formlist+=[ChallengeModelForm(user=user)]

    return render_to_response('propose_new_challenge.html', {'IntegrityErrorMSG:IntegrityErrorMSG''problem_criteria':problem_criteria,'captain_conflict':captain_conflict,'my_teams_as_cap':my_teams_as_cap,'is_a_game':is_a_game,'registrant':registrant,'cancaptain':cancaptain,'cansk8':cansk8,'upcoming_registrants':upcoming_registrants,'MAX_CAPTAIN_LIMIT':MAX_CAPTAIN_LIMIT,'formlist':formlist},context_instance=RequestContext(request))

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
