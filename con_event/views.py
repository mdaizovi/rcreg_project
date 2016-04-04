from django.shortcuts import render,render_to_response, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.db import connection as dbconnection
from con_event.forms import RegistrantProfileForm
from con_event.models import Blog, Con, Registrant,Blackout
import collections
import datetime

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
            these_date_strings=[]
            date_dict={}
            these_dates=this_con.get_date_range()
            for date in these_dates:
                #don't change the way you convert to string, this method needs to be the same for update_blackouts to work.
                string_of_date=date.strftime("%B %d, %Y")
                ampmitems=request.POST.getlist(string_of_date)
                #print "ampmitems",ampmitems
                if string_of_date not in request.POST:
                    #If date not in post at all, assume both boxes unchecked.
                    date_dict[string_of_date]=["AM","PM"]
                else:#assuming there's an ampmitem list, bc the date is in post
                    if "AM" not in ampmitems:
                        date_dict[string_of_date]=["AM"]
                    elif "PM" not in ampmitems:
                        date_dict[string_of_date]=["PM"]
            this_reg.update_blackouts(date_dict)

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
        datelist=None
        form = RegistrantProfileForm(instance=registrant)

        #maybe i should only run this is con hasn't happened yet?
        if (registrant.con.start > datetime.date.today()):
            if registrant.captain.all() or user.is_a_coach_this_con(registrant.con):
                datelist=registrant.con.get_date_range()
                for bo in registrant.blackout.all():
                    bo_list.append((bo.date,bo.ampm,None,"Available "+bo.ampm))
                for date in datelist:
                    if (date,"AM",None,"Available AM") not in bo_list:
                        #if no BO, that means they're available, check the box in the template. None for item 2 will not check the box.
                        bo_list.append((date,"AM","checked","Available AM"))
                    if (date,"PM",None,"Available PM") not in bo_list:
                        bo_list.append((date,"PM","checked","Available PM"))
                bo_list.sort()

        else:
            datelist=None
            bo_list=None

        registrant_dict={'bo_list':bo_list,'datelist':datelist,'con':registrant.con, 'registrant':registrant,'form':form}
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
