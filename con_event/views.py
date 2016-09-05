import datetime

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from con_event.forms import RegistrantProfileForm, AvailabilityForm
from con_event.BPTExcel import BPTUploadForm
from con_event.models import Blog, Con, Registrant, Blackout
from swingtime.models import Occurrence

#-------------------------------------------------------------------------------
@login_required
def upload_reg(request):
    """Easy upload for uplaoding an Excel sheet into DB.
    Excel sheet must be XLSX and look exactly like BPT reports did in 2016,
    otherwise file will be rejected.
    """
    save_attempt = False
    save_success = False
    reg_added = []
    if request.method == 'POST':
        form = BPTUploadForm(request.POST, request.FILES)
        save_attempt = True
        # Don't touch the my valid/is valid, it has to be that way
        if form.my_valid():
            if form.is_valid():
                wb = form.make_registrants()
                save_success = True

                filename = ('RollerTron Upload %s.xlsx'
                        % (datetime.date.today().strftime("%B %d %Y"))
                        )
                response = (HttpResponse(
                        content_type='application/vnd.openxmlformats-officedocument\
                        .spreadsheetml.sheet')
                        )
                response['Content-Disposition'] = ('attachment; filename=%s'
                        % (filename)
                        )

                wb.save(response)
                return response
        else:  # If not my_valid
            form = BPTUploadForm(request.POST)
    else:  # If not POST
        form = BPTUploadForm()

    context_dict = {
        'save_attempt': save_attempt,
        'save_success': save_success,
        'reg_added': reg_added,
        'form': form
        }

    return (render_to_response(
            'upload_reg.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
def CheapAirDynamic(request):
    '''Looks nice to fill the flight search with upcoming con data;
    search doesn't work. Think it's their fault, not mine, though'''
    most_upcoming = Con.objects.most_upcoming()
    context_dict = {'most_upcoming': most_upcoming}

    return (render_to_response(
            'CheapAirDynamic.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
def index(request):
    most_upcoming = Con.objects.most_upcoming()
    blog = Blog.objects.latest('date')
    context_dict = {'most_upcoming': most_upcoming, 'blog': blog}

    return (render_to_response(
            'index.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
@login_required
def WTFAQ(request):
    """Private FAQ that only bosses (user.is_a_boss) can see."""

    user = request.user
    context_dict = {'user': user}

    return (render_to_response(
            'WTFAQ.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
def announcement(request, slugname):
    """Blog by another name. Individual announcement view."""

    blog = Blog.objects.get(slugname=slugname)
    next_blog, previous_blog = blog.get_next_and_previous()
    context_dict = {'previous_blog': previous_blog,
                    'next_blog': next_blog,
                    'blog': blog
                    }

    return (render_to_response(
            'announcement.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
def all_announcements(request):
    """Blog by another name. All announcements view."""
    context_dict = {'blogs': Blog.objects.all()}

    return (render_to_response(
            'all_announcements.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
@login_required
def registrant_profile(request):
    '''Gets all registrants for user and displays them.
    Only the first in the list, presumably most recent, is editable--
    all others are disabled.
    If Users ever need to be able to edit 2 Registrants at once,
    like for overlapping Cons, it will need to be rewritten.
    problem_criteria / potential_conflicts / captain_conflict refers to
    whether they are changing ther skill or gender in such a way that would make
    them ineligible for a Challenge they're captaining or on roster for.
    '''

    save_attempt = False
    save_success = False
    this_reg = None  # Most recent; only one that can be edited or saved.
    user = request.user
    upcoming = Con.objects.upcoming_cons()
    registrant_dict_list = []
    problem_criteria = None
    potential_conflicts = None
    captain_conflict = None

    if request.method == 'POST':
        save_attempt = True
        this_reg = Registrant.objects.get(pk=request.POST['registrant_id'])
        this_con = this_reg.con

        # The only attributes users can edit themselves are
        # skill, gender, and sk8number.
        if 'skill' in request.POST:
            if request.POST['skill'] in [None, "None", "", u'']:
                this_reg.skill = None
            else:
                this_reg.skill = request.POST['skill']
        if 'gender' in request.POST:
            this_reg.gender = request.POST['gender']
        if 'sk8number' in request.POST:
            this_reg.sk8number = request.POST['sk8number']
        problem_criteria, potential_conflicts, captain_conflict = (
                this_reg.criteria_conflict()
                )

        # Only captains and coaches will have a blackouts box.
        # Important because no avilability check means a blackout is made
        # If there's no check (because no form), a blackout will be made,
        # and then you have thousands of blackouts for people who
        # didn't even know, didn't even see the form.
        if 'blackouts_visible' in request.POST:
            bo_tup_list = []
            available = []
            for key, value in request.POST.items():
                if value == u'on':
                    available.append(key)

            for date in this_con.get_date_range():
                ampmlist = []
                if str(date) + "-am" not in available:
                    # If it's not checked, that means they de-slescted that day
                    # and a blackout needs to be made.
                    # If it's checked, that day is available,
                    # don't want a blackout for that day.
                    # A little counter-intuitive, hence comments.
                    bo_tup_list.append((date, "AM"))
                if str(date) + "-pm" not in available:
                    bo_tup_list.append((date, "PM"))
            this_reg.update_blackouts(bo_tup_list)

        # captain_conflict is a check to see if they are
        # making themselves ineligible for a challenge they are captain of.
        if not captain_conflict:
            # problem_criteria would be either 'skill' or 'gender',
            # potential_conflicts would be a list of the ineligible challenges
            if problem_criteria or potential_conflicts:
                if 'confirm save' in request.POST:
                    # conflict_sweep drops them from the roster.
                    # captains don't have this option.
                    conflict_sweep = this_reg.conflict_sweep()
                    this_reg.save()
                    if conflict_sweep:
                        save_success = True
                else:
                    hidden_forms = [
                            (RegistrantProfileForm(
                                    request.POST or None,
                                    instance=this_reg)
                                    )
                            ]

                    context_dict = {'registrant': this_reg,
                            'hidden_forms': hidden_forms,
                            'problem_criteria': problem_criteria,
                            'potential_conflicts': potential_conflicts
                            }

                    return (render_to_response(
                            'conflict_warning.html',
                            context_dict,
                            context_instance=RequestContext(request))
                            )

            else:  #if no problem criteria
                this_reg.save()
                save_success = True

    registrant_list = list(user.registrant_set.all())
    for registrant in registrant_list:
        bo_list = []
        bo_form_list = []
        datelist = None
        form = RegistrantProfileForm(instance=registrant)

        # Only runs if con hasn't happened yet,
        # since blackouts are used for scheduling.
        # Could also be disabled after schedule is final, I suppose.
        if (registrant.con.start > datetime.date.today()):
            # Only collect blackouts for coaches and captains
            if (registrant.captain.all() or
                    user.is_a_coach_this_con(registrant.con)
                    ):
                datelist = registrant.con.get_date_range()
                for bo in registrant.blackout.all():
                    bo_list.append((bo.date, bo.ampm))

                for date in datelist:
                    initial = {}
                    if (date, "AM") in bo_list:
                        initial["am"] = False
                    if (date,"PM") in bo_list:
                        initial["pm"] = False
                    availabilityform = (
                            AvailabilityForm(
                                    date=date,
                                    initial=initial,
                                    prefix=str(date)
                                    )
                            )
                    bo_form_list.append(availabilityform)
        else:  # If con has already happened.
            datelist = None
            bo_list = None

        registrant_dict = {
                'bo_form_list': bo_form_list,
                'datelist': datelist,
                'con': registrant.con,
                'registrant': registrant,
                'form': form
                }
        registrant_dict_list.append(registrant_dict)

    upcoming_registrants = user.upcoming_registrants()
    # active tells the template which con to display first.
    if save_success:
        active = this_reg.con
    elif upcoming_registrants and len(upcoming_registrants) > 1:
        active = Con.objects.most_upcoming()
    else:
        try:
            most_upcoming_reg = registrant_list[0]
            active = most_upcoming_reg.con
        except:
            active = None

    context_dict = {
            'captain_conflict': captain_conflict,
            'this_reg': this_reg,
            'problem_criteria': problem_criteria,
            'potential_conflicts': potential_conflicts,
            'upcoming': upcoming,
            'active': active,
            'save_attempt': save_attempt,
            'save_success': save_success,
            'user': user,
            'registrant_dict_list': registrant_dict_list
            }

    return (render_to_response(
            'registrant_profile.html',
            context_dict,
            context_instance=RequestContext(request))
            )

#-------------------------------------------------------------------------------
@login_required
def know_thyself(request, con_id=None):
    """Some basic Con analytics.
    Hideous long code in the view because this is the one and only time
    this data is ever necessary, no reason to write methods over it.
    It's hard to read to cut down on DB hits; my apologies.
    I tossed it at the end of the file so no one ever has to look at it.
    """
    if con_id:
        try:
            con=Con.objects.get(pk=con_id)
        except:
            return render_to_response('know_thyself.html', {},context_instance=RequestContext(request))
    else:
        con=Con.objects.most_upcoming()

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
        if len(all_r)>0:
            attendee[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            attendee[tup[0]]="0"

    first={}
    all_first=first_mvp+first_sk8+first_offsk8
    for tup in [ ("total",all_first),("mvp",first_mvp), ("sk8",first_sk8),("offsk8",first_offsk8)]:
        if len(all_r)>0:
            first[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            first[tup[0]]="0"

    returning={}
    all_returning=return_mvp+return_sk8+return_offsk8
    for tup in [ ("total",all_returning),("mvp",return_mvp), ("sk8",return_sk8),("offsk8",return_offsk8)]:
        if len(all_r)>0:
            returning[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            returning[tup[0]]="0"

    usintl={}
    all_usintl=us_intl_mvp+us_intl_sk8+us_intl_offsk8
    for tup in [ ("total",all_usintl),("mvp",us_intl_mvp), ("sk8",us_intl_sk8),("offsk8",us_intl_offsk8)]:
        if len(all_r)>0:
            usintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            usintl[tup[0]]="0"

    foreignintl={}
    all_foreignintl=foreign_intl_mvp+foreign_intl_sk8+foreign_intl_offsk8
    for tup in [ ("total",all_foreignintl),("mvp",foreign_intl_mvp), ("sk8",foreign_intl_sk8),("offsk8",foreign_intl_offsk8)]:
        if len(all_r)>0:
            foreignintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            foreignintl[tup[0]]="0"

    unspecintl={}
    all_unspecintl=unspec_intl_mvp+unspec_intl_sk8+unspec_intl_offsk8
    for tup in [ ("total",all_unspecintl),("mvp",unspec_intl_mvp), ("sk8",unspec_intl_sk8),("offsk8",unspec_intl_offsk8)]:
        if len(all_r)>0:
            unspecintl[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            unspecintl[tup[0]]="0"

    female={}
    all_female=female_mvp+female_sk8+female_offsk8
    for tup in [ ("total",all_female),("mvp",female_mvp), ("sk8",female_sk8),("offsk8",female_offsk8)]:
        if len(all_r)>0:
            female[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            female[tup[0]]="0"

    male={}
    all_male=male_mvp+male_sk8+male_offsk8
    for tup in [ ("total",all_male),("mvp",male_mvp), ("sk8",male_sk8),("offsk8",male_offsk8)]:
        if len(all_r)>0:
            male[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            male[tup[0]]="0"

    nonbinary={}
    all_nonbinary=nonbinary_mvp+nonbinary_sk8+nonbinary_offsk8
    for tup in [ ("total",all_nonbinary),("mvp",nonbinary_mvp), ("sk8",nonbinary_sk8),("offsk8",nonbinary_offsk8)]:
        if len(all_r)>0:
            nonbinary[tup[0]]="%s (%s percent)" % (str(len( tup[1] )), "{0:.2f}".format( (float(len( tup[1] ))/(len( all_r ))*100 ) ) )
        else:
            nonbinary[tup[0]]="0"

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

    for k,v in state_dict.iteritems():
        length=len(v)
        if len(all_r)>0:
            percent_str="{0:.2f}".format( (float(len( v ))/(len( all_r ))*100 ) )
        else:
            percent_str="0"

        this_str="%s: %s Attendees, (%s percent)" % (k.name, str(length),percent_str)
        tup=(length,k.name,percent_str)
        state_tups.append(tup)

    state_tups.sort(reverse=True)
    for t in state_tups:
        states.append(t[1])

    occurrences=list(Occurrence.objects.filter(start_time__gte=con.start,end_time__lte=con.end).select_related('challenge').select_related('challenge__roster1').prefetch_related('challenge__roster1__participants').select_related('challenge__roster2').prefetch_related('challenge__roster2__participants').select_related('training').prefetch_related('training__coach').prefetch_related('training__registered').prefetch_related('training__auditing')) #17 hits

    challenges=[]
    trainings=[]
    for o in occurrences:
        if o.challenge:
             challenges.append(o)
        elif o.training:
            trainings.append(o)

    c_dur=0
    cr_total=0
    games=[]
    for o in challenges:
        c_dur+=float(o.challenge.duration)
        for roster in [o.challenge.roster1,o.challenge.roster2]:
            if roster:
                cr_total+=roster.participants.count()
        if o.challenge.is_a_game:
            games.append(o)
    c_tup=((len(challenges)-len(games)),c_dur, cr_total,len(games))


    t_dur=0
    tr_total=0
    t_coaches=[]
    for o in trainings:
        t_dur+=float(o.training.duration)
        for c in o.training.coach.all():
            if c not in t_coaches:
                t_coaches.append(c)

        if hasattr(o, 'registered'):
            tr_total+=o.registered.participants.count()
        elif hasattr(o, 'auditing'):
            tr_total+=o.registered.participants.count()

    t_tup=(len(trainings),t_dur, tr_total,len(t_coaches))

    return render_to_response('know_thyself.html', {'t_tup':t_tup,'c_tup':c_tup,'state_tups':state_tups,'states':states,'countries':countries,'female':female,'male':male,'nonbinary':nonbinary,'unspecintl':unspecintl,
        'foreignintl':foreignintl,'usintl':usintl,'returning':returning,'first':first,'attendee':attendee,'con':con,'con_list':list(Con.objects.all())},context_instance=RequestContext(request))
