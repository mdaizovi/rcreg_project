from django.shortcuts import render,render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.db import connection as dbconnection
from con_event.forms import RegistrantProfileForm,AvailabilityForm
from con_event.models import Blog, Con, Registrant,Blackout
import collections
import datetime

def know_thyself(request, con_id=None):
    if con_id:
        try:
            con=Con.objects.get(pk=con_id)
        except:
            return render_to_response('know_thyself.html', {},context_instance=RequestContext(request))
    else:
        #con=Con.objects.most_recent()
        con=Con.objects.most_upcoming()
    #print "dbc0:", len(dbconnection.queries)
    #all_r=list(Registrant.objects.filter(con=con)) #800 db hits
    #all_r=list(Registrant.objects.filter(con=con).select_related('user')) #400 db hits
    all_r=list(Registrant.objects.filter(con=con).select_related('country').select_related('state').select_related('user').prefetch_related('user__registrant_set')) #6 db hits!

    mvp_pass=[]
    first_mvp=[]
    return_mvp=[]
    us_intl_mvp=[]
    foreign_intl_mvp=[]
    unspec_intl_mvp=[]
    male_mvp=[]
    female_mvp=[]
    nonbinary_mvp=[]

    sk8_pass=[]
    first_sk8=[]
    return_sk8=[]
    us_intl_sk8=[]
    foreign_intl_sk8=[]
    unspec_intl_sk8=[]
    male_sk8=[]
    female_sk8=[]
    nonbinary_sk8=[]

    offsk8_pass=[]
    first_offsk8=[]
    return_offsk8=[]
    us_intl_offsk8=[]
    foreign_intl_offsk8=[]
    unspec_intl_offsk8=[]
    male_offsk8=[]
    female_offsk8=[]
    nonbinary_offsk8=[]

    americans=[]

    #do all splitting in 1 place so only 1 db hit.
    for r in all_r:
        if r.pass_type=="MVP":
            mvp_pass.append(r)
            if len(r.user.registrant_set.all())>1:
                return_mvp.append(r)
            else:
                first_mvp.append(r)

            if r.intl:
                if r.country and r.country.slugname != "US":
                    foreign_intl_mvp.append(r)
                elif r.country and r.country.slugname == "US":
                    us_intl_mvp.append(r)
                    if r.state:
                        americans.append(r)
                else:
                    unspec_intl_mvp.append(r)
            elif r.state:
                americans.append(r)

            if r.gender and r.gender=="Male":
                male_mvp.append(r)
            elif r.gender and r.gender=="Female":
                female_mvp.append(r)
            else:
                nonbinary_mvp.append(r)

        elif r.pass_type=="Skater":
            sk8_pass.append(r)
            if len(r.user.registrant_set.all())>1:
                return_sk8.append(r)
            else:
                first_sk8.append(r)

            if r.intl:
                if r.country and r.country.slugname != "US":
                    foreign_intl_sk8.append(r)
                elif r.country and r.country.slugname == "US":
                    us_intl_sk8.append(r)
                    if r.state:
                        americans.append(r)
                else:
                    unspec_intl_sk8.append(r)
            elif r.state:
                americans.append(r)

            if r.gender and r.gender=="Male":
                male_sk8.append(r)
            elif r.gender and r.gender=="Female":
                female_sk8.append(r)
            else:
                nonbinary_sk8.append(r)

        elif r.pass_type=="Offskate":
            offsk8_pass.append(r)
            if len(r.user.registrant_set.all())>1:
                return_offsk8.append(r)
            else:
                first_offsk8.append(r)

            if r.intl:
                if r.country and r.country.slugname != "US":
                    foreign_intl_offsk8.append(r)
                elif r.country and r.country.slugname == "US":
                    us_intl_offsk8.append(r)
                    if r.state:
                        americans.append(r)
                else:
                    unspec_intl_offsk8.append(r)
            elif r.state:
                americans.append(r)

            if r.gender and r.gender=="Male":
                male_offsk8.append(r)
            elif r.gender and r.gender=="Female":
                female_offsk8.append(r)
            else:
                nonbinary_offsk8.append(r)

    attendee={}
    for tup in [ ("total",all_r),("mvp",mvp_pass), ("sk8",sk8_pass),("offsk8",offsk8_pass)]:
        attendee[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    first={}
    all_first=first_mvp+first_sk8+first_offsk8
    for tup in [ ("total",all_first),("mvp",first_mvp), ("sk8",first_sk8),("offsk8",first_offsk8)]:
        first[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    returning={}
    all_returning=return_mvp+return_sk8+return_offsk8
    for tup in [ ("total",all_returning),("mvp",return_mvp), ("sk8",return_sk8),("offsk8",return_offsk8)]:
        returning[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    usintl={}
    all_usintl=us_intl_mvp+us_intl_sk8+us_intl_offsk8
    for tup in [ ("total",all_usintl),("mvp",us_intl_mvp), ("sk8",us_intl_sk8),("offsk8",us_intl_offsk8)]:
        usintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    foreignintl={}
    all_foreignintl=foreign_intl_mvp+foreign_intl_sk8+foreign_intl_offsk8
    for tup in [ ("total",all_foreignintl),("mvp",foreign_intl_mvp), ("sk8",foreign_intl_sk8),("offsk8",foreign_intl_offsk8)]:
        foreignintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    unspecintl={}
    all_unspecintl=unspec_intl_mvp+unspec_intl_sk8+unspec_intl_offsk8
    for tup in [ ("total",all_unspecintl),("mvp",unspec_intl_mvp), ("sk8",unspec_intl_sk8),("offsk8",unspec_intl_offsk8)]:
        unspecintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    female={}
    all_female=female_mvp+female_sk8+female_offsk8
    for tup in [ ("total",all_female),("mvp",female_mvp), ("sk8",female_sk8),("offsk8",female_offsk8)]:
        female[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
    male={}
    all_male=male_mvp+male_sk8+male_offsk8
    for tup in [ ("total",all_male),("mvp",male_mvp), ("sk8",male_sk8),("offsk8",male_offsk8)]:
        male[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
    nonbinary={}
    all_nonbinary=nonbinary_mvp+nonbinary_sk8+nonbinary_offsk8
    for tup in [ ("total",all_nonbinary),("mvp",nonbinary_mvp), ("sk8",nonbinary_sk8),("offsk8",nonbinary_offsk8)]:
        nonbinary[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )

    country_dict={}
    for r in all_foreignintl:
        if r.country not in country_dict:
            country_dict[r.country]=[r]
        else:
            templist=country_dict.get(r.country)
            templist.append(r)
            country_dict[r.country]=list(templist)

    countries=[]
    for k,v in country_dict.iteritems():
        this_str="%s: %s Attendees" % (k.name, len(v))
        countries.append(this_str)
    countries.sort()

    state_dict={}
    for r in americans:
        if r.state not in state_dict:
            state_dict[r.state]=[r]
        else:
            templist=state_dict.get(r.state)
            templist.append(r)
            state_dict[r.state]=list(templist)

    states=[]
    state_tups=[]
    # for k,v in state_dict.iteritems():
    #     length=len(v)
    #     percent_str="{0:.2f}".format( (float(len( v ))/(len( all_r ))*100 ) )
    #     this_str="%s: %s Attendees, (%s percent)" % (k.name, str(length),percent_str)
    #     tup=(length,this_str)
    #     state_tups.append(tup)

    for k,v in state_dict.iteritems():
        length=len(v)
        percent_str="{0:.2f}".format( (float(len( v ))/(len( all_r ))*100 ) )
        this_str="%s: %s Attendees, (%s percent)" % (k.name, str(length),percent_str)
        tup=(length,k.name,percent_str)
        state_tups.append(tup)


    state_tups.sort(reverse=True)
    for t in state_tups:
        states.append(t[1])


    #print "dbc1:", len(dbconnection.queries)
    return render_to_response('know_thyself.html', {'state_tups':state_tups,'states':states,'countries':countries,'female':female,'male':male,'nonbinary':nonbinary,'unspecintl':unspecintl,'foreignintl':foreignintl,'usintl':usintl,'returning':returning,'first':first,'attendee':attendee,'con':con,'con_list':list(Con.objects.all())},context_instance=RequestContext(request))

def CheapAirDynamic(request):
    '''this looks nice to fill the flight search with upcoming con data, but the search doesn't work
    i think it's their fault, not mine, though'''
    most_upcoming=Con.objects.most_upcoming()
    return render_to_response('CheapAirDynamic.html', {'most_upcoming':most_upcoming},context_instance=RequestContext(request))

def index(request):
    most_upcoming=Con.objects.most_upcoming()
    blog=Blog.objects.latest('date')
    return render_to_response('index.html', {'most_upcoming':most_upcoming,'blog':blog},context_instance=RequestContext(request))

@login_required
def WTFAQ(request):
    user=request.user
    return render_to_response('WTFAQ.html', {'user':user},context_instance=RequestContext(request))


def announcement(request, slugname):
    blog=Blog.objects.get(slugname=slugname)
    next_blog,previous_blog=blog.get_next_and_previous()
    return render_to_response('announcement.html', {'previous_blog':previous_blog,'next_blog':next_blog,'blog':blog},context_instance=RequestContext(request))

def all_announcements(request):
    return render_to_response('all_announcements.html', {'blogs':Blog.objects.all()},context_instance=RequestContext(request))

@login_required
def registrant_profile(request):
    '''Thie view feels dicey. It gets all registrants for user and displays them. Only the first in th list,
    presumably most recent, is editable--all others are disabled.
    You can modify and change data and presumable only the most recent Registrant will be saved, but it feels like this
    is precarious and could massively fuck up someday.
    form.media relates to the datetime widget. I don't now why it only works on the first tab, but I made all others disbled anyway, so no problem?
    '''
    save_attempt=False
    save_success=False
    this_reg=None#this is the one that gets selected if you're saving something
    user=request.user
    upcoming=Con.objects.upcoming_cons()
    registrant_dict_list=[]
    problem_criteria=None
    potential_conflicts=None
    captain_conflict=None
    selection=None


    if request.method == 'POST':
        selection = request.POST.copy()
        #print "selection", selection
        #selectiondict=dict(selection.lists())
        #print "selectiondict: ",selectiondict

        save_attempt=True
        this_reg=Registrant.objects.get(pk=request.POST['registrant_id'])
        this_con=this_reg.con
        #for some fucking reason couldn't get the goddamed modelform to act like a real modelform
        #so i write hack aorund only updating the only 2 fields I want to be able to update, anyway.
        #which is fine, I guess bc otherwise I had all kinds of shit to make sure pass type and intl didn't get changed.
        if 'skill' in request.POST:
            if request.POST['skill'] in [None,"None","",u'']:
                this_reg.skill=None
            else:
                this_reg.skill=request.POST['skill']
        if 'gender' in request.POST:
            this_reg.gender=request.POST['gender']
        if 'sk8number' in request.POST:
            this_reg.sk8number=request.POST['sk8number']
        problem_criteria,potential_conflicts,captain_conflict=this_reg.criteria_conflict()

        if 'blackouts_visible' in request.POST:#I was accidentaly saving blackout unavailable days for people who didn't even see them! shit!
            bo_tup_list=[]
            available=[]
            for key, value in request.POST.items():
                if value==u'on':
                    available.append(key)

            for date in this_con.get_date_range():
                ampmlist=[]
                if str(date)+"-am" not in available:
                    #If it's not checked that means a Blackout needs to be made.
                    #If it's checked, that day is available, don't want a blakcout for that day.
                    bo_tup_list.append((date,"AM"))
                if str(date)+"-pm" not in available:
                    bo_tup_list.append((date,"PM"))
            this_reg.update_blackouts(bo_tup_list)

        if not captain_conflict:
            if problem_criteria or potential_conflicts:
                if 'confirm save' in request.POST:
                    conflict_sweep=this_reg.conflict_sweep()
                    this_reg.save()
                    if conflict_sweep:
                        save_success=True
                else:
                    hidden_forms=[RegistrantProfileForm(request.POST or None, instance=this_reg)]
                    #hidden_form=RegistrantProfileForm(request.POST or None, instance=this_reg)
                    return render_to_response('conflict_warning.html',{'registrant':this_reg,'hidden_forms':hidden_forms,'problem_criteria':problem_criteria,'potential_conflicts':potential_conflicts},context_instance=RequestContext(request))

            else:#if no problem criteria
                this_reg.save()
                save_success=True

    registrant_list= list(user.registrant_set.all())
    for registrant in registrant_list:
        bo_list=[]
        bo_form_list=[]
        datelist=None
        form = RegistrantProfileForm(instance=registrant)

        #maybe i should only run this is con hasn't happened yet?
        if (registrant.con.start > datetime.date.today()):
            if registrant.captain.all() or user.is_a_coach_this_con(registrant.con):
                datelist=registrant.con.get_date_range()
                for bo in registrant.blackout.all():
                    bo_list.append((bo.date,bo.ampm))

                for date in datelist:
                    initial={}
                    if (date,"AM") in bo_list:
                        initial["am"]=False
                    if (date,"PM") in bo_list:
                        initial["pm"]=False
                    availabilityform=AvailabilityForm(date=date,initial=initial,prefix=str(date))
                    bo_form_list.append(availabilityform)
        else:
            datelist=None
            bo_list=None

        registrant_dict={'bo_form_list':bo_form_list,'datelist':datelist,'con':registrant.con, 'registrant':registrant,'form':form}
        registrant_dict_list.append(registrant_dict)

    upcoming_registrants=user.upcoming_registrants()
    if save_success:
        active=this_reg.con
    elif upcoming_registrants and len(upcoming_registrants)>1:
        active=Con.objects.most_upcoming()
    else:
        try:
            most_upcoming_reg=registrant_list[0]
            active=most_upcoming_reg.con
        except:
            active=None


    return render_to_response('registrant_profile.html',{'captain_conflict':captain_conflict,'this_reg':this_reg,'problem_criteria':problem_criteria, 'potential_conflicts':potential_conflicts,'upcoming':upcoming,'active':active,'save_attempt':save_attempt,'save_success':save_success,'user':user,'registrant_dict_list':registrant_dict_list},context_instance=RequestContext(request))
