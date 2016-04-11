import calendar
import itertools
import logging
import collections
from datetime import datetime, timedelta, time

from django import http
from django.db import models
from django.template.context import RequestContext
from django.shortcuts import get_object_or_404, render, redirect,HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
#from django.forms import modelformset_factory

from swingtime.models import Event, Occurrence
from swingtime import utils, forms
from swingtime.conf import settings as swingtime_settings

from con_event.models import Con
from con_event.forms import ConSchedStatusForm
from scheduler.models import Location, Training, Challenge
from scheduler.forms import ChalStatusForm,TrainStatusForm

from dateutil import parser

if swingtime_settings.CALENDAR_FIRST_WEEKDAY is not None:
    calendar.setfirstweekday(swingtime_settings.CALENDAR_FIRST_WEEKDAY)


#-------------------------------------------------------------------------------
@login_required
def chal_submit(
    request,
    template='swingtime/chal_submit.html',
    con_id=None,
    **extra_context
):

    if con_id:
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Challenge.objects.filter(con=con, RCrejected=False).exclude(roster1=None).exclude(roster2=None).exclude(submitted_on=None).order_by('submitted_on')
    q_od  = collections.OrderedDict()
    for c in q:
        q_od[c]=ChalStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCrejected==True:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Challenge.objects.filter(con=con, RCaccepted=True).exclude(submitted_on=None).order_by('submitted_on')
    q_od = collections.OrderedDict()
    for c in q:
        q_od[c]=ChalStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCaccepted==False:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Challenge.objects.filter(con=con, RCrejected=True).exclude(submitted_on=None).order_by('submitted_on')
    q_od = collections.OrderedDict()
    for c in q:
        q_od[c]=ChalStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCrejected==False:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Training.objects.filter(con=con, RCrejected=False).order_by('created_on')
    q_od  = collections.OrderedDict()
    for c in q:
        q_od[c]=TrainStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCrejected==True:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Training.objects.filter(con=con, RCaccepted=True).order_by('created_on')
    q_od = collections.OrderedDict()
    for c in q:
        q_od[c]=TrainStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCaccepted==False:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    q=Training.objects.filter(con=con, RCrejected=True).order_by('created_on')
    q_od = collections.OrderedDict()
    for c in q:
        q_od[c]=TrainStatusForm(request.POST or None, instance=c,prefix=str(c.pk))

    save_success=0
    if request.method == 'POST':
        for form in q_od.values():
            if form.is_valid():
                this_instance=form.save()
                save_success+=1
                if this_instance.RCrejected==False:
                    del q_od[this_instance]#remove if no longer accepted

    new_context={"save_success":save_success,"q_od":q_od,"con":con,"con_list":Con.objects.all()}
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    extra_context['con'] = con
    extra_context['con_list'] = Con.objects.all()
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
        con=Con.objects.get(pk=con_id)
    else:
        con=Con.objects.most_upcoming()

    challenges=Occurrence.objects.filter(event__challenge__con=con)
    trainings=Occurrence.objects.filter(event__training__con=con)
    new_context={"activities":[challenges,trainings],"con":con,"con_list":Con.objects.all()}
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

    if request.method == 'POST':
        form = form_class(request.POST, instance=con)
        if form.is_valid():
            form.save()
            save_success=True
            return render(request, template, {'save_success':save_success,'con':con, 'con_list':Con.objects.all(),'form': form})

    else:
        form = form_class(instance=con)

    return render(request, template, {'save_success':save_success,'con':con,'con_list':Con.objects.all(),'form': form})


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
def event_listing(
    request,
    template='swingtime/event_list.html',
    events=None,
    **extra_context
):
    '''
    View all ``events``.

    If ``events`` is a queryset, clone it. If ``None`` default to all ``Event``s.

    Context parameters:

    ``events``
        an iterable of ``Event`` objects

    ... plus all values passed in via **extra_context
    '''
    if events is None:
        events = Event.objects.all()

    extra_context['events'] = events
    return render(request, template, extra_context)


#-------------------------------------------------------------------------------
@login_required
def event_view(
    request,
    pk,
    template='swingtime/event_detail.html',
    event_form_class=forms.EventForm,
    recurrence_form_class=forms.MultipleOccurrenceForm,
    save_success=False,
):
    '''
    View an ``Event`` instance and optionally update either the event or its
    occurrences.

    Context parameters:

    ``event``
        the event keyed by ``pk``

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences
    '''
    event = get_object_or_404(Event, pk=pk)
    event_form = recurrence_form = None
    if request.method == 'POST':
        if '_update' in request.POST:
            event_form = event_form_class(request.POST, instance=event)
            if event_form.is_valid():
                event_form.save(event)
                save_success=True
                return http.HttpResponseRedirect(request.path)
        elif '_add' in request.POST:
            recurrence_form = recurrence_form_class(request.POST)
            if recurrence_form.is_valid():
                recurrence_form.save(event)
                save_success=True
                return http.HttpResponseRedirect(request.path)
        else:
            return http.HttpResponseBadRequest('Bad Request')

    data = {
        'save_success':save_success,#probably doesn't run
        'event': event,
        'event_form': event_form or event_form_class(instance=event),
        'recurrence_form': recurrence_form or recurrence_form_class(initial={'dtstart': datetime.now()})
    }
    return render(request, template, data)


#-------------------------------------------------------------------------------
@login_required
def occurrence_view(
    request,
    event_pk,
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
    occurrence = get_object_or_404(Occurrence, pk=pk, event__pk=event_pk)
    conflict_free=False
    conflict={}

    if request.method == 'POST':
        form = form_class(request.POST, instance=occurrence)
        if form.is_valid():
            if "update" in request.POST:
                form.save()
                save_success=True
                #return render(request, template, {'save_success':save_success,'occurrence': occurrence, 'form': form})
            elif "check" in request.POST:
                figurehead_conflict=occurrence.figurehead_conflict()
                if figurehead_conflict:
                    conflict["figurehead_conflict"]=figurehead_conflict
                participant_conflict=occurrence.participant_conflict()
                if participant_conflict:
                    conflict["participant_conflict"]=participant_conflict
                blackout_conflict=occurrence.blackout_conflict()
                if blackout_conflict:
                    conflict["blackout_conflict"]=blackout_conflict
                if len(conflict)<=0:
                    conflict_free=True
    else:
        form = form_class(instance=occurrence)

    return render(request, template, {'conflict_free':conflict_free,'conflict':conflict,'save_success':save_success,'occurrence': occurrence, 'form': form})


#-------------------------------------------------------------------------------
@login_required
def add_event(
    request,
    template='swingtime/add_event.html',
    event_form_class=forms.EventForm,
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
    save_success=False
    dtstart = None
    drend=None
    training=None
    challenge=None
    location=None
    conflict={}
    conflict_free=False
    no_list=["",u'',None,"None"]
    recurrence_dict={}
    event_dict={}
    get_dict={}
    #########fetch all get values as intials##########
    if 'dtstart' in request.GET:
        try:
            dtend = dtstart = parser.parse(request.GET['dtstart'])
            get_dict["start_time"]=dtstart
            recurrence_dict["start_time"]=dtstart
            recurrence_dict["end_time"]=dtend#setting initial as same, chang elater d/t post info or model method
        except(TypeError, ValueError) as exc:
            # TODO: A badly formatted date is passed to add_event
            logging.warning(exc)
    if "training" in request.GET and request.GET['training'] not in no_list:
        training=Training.objects.get(pk=request.GET['training'])
        get_dict['training']=training
        event_dict['training']=training
    if "challenge" in request.GET and request.GET['challenge'] not in no_list:
        challenge=Challenge.objects.get(pk=request.GET['challenge'])
        get_dict['challenge']=challenge
        event_dict['challenge']=challenge
    if "location" in request.GET and request.GET['location'] not in no_list:
        location=Location.objects.get(pk=request.GET['location'])
        get_dict['location']=location
        recurrence_dict['location']=location
    #print "get dict",get_dict
    ########done fetching get values#########

    #initial offering, might get overwritten w/post
    event_form = event_form_class(date=dtstart, initial=event_dict)
    recurrence_form = recurrence_form_class(initial=recurrence_dict)
    ##########################

    if request.method == 'POST':
        selection = request.POST.copy()
        print "selection", selection

        dtend_post=[u'end_time_1',u'end_time_0_year',u'end_time_0_month','end_time_0_day']
        if len( set(dtend_post).intersection(request.POST.keys())) > 0:
            dtend_str=request.POST['end_time_0_year']+"-"+request.POST['end_time_0_month']+"-"+request.POST['end_time_0_day']+"T"+request.POST['end_time_1']
            dtend=parser.parse(dtend_str)
            recurrence_dict['end_time']=dtend#I think this is unnecessary

        #these will override the train/chal set from get, if they're there.
        if "challenge" in request.POST and request.POST['challenge'] not in no_list:
            challenge=Challenge.objects.get(pk=request.POST['challenge'])
        if "training" in request.POST and request.POST['training'] not in no_list:
            training=Training.objects.get(pk=request.POST['training'])

        event_form = event_form_class(request.POST,date=dtstart)
        recurrence_form = recurrence_form_class(request.POST)

        if event_form.is_valid() and recurrence_form.is_valid():
            try:#both chal and train could be a thing, or none
                print "trying t get event with chal/t"
                event=Event.objects.get(challenge=challenge, training=training)
            except ObjectDoesNotExist:
                print "does not exist"
                event = event_form.save(commit=False)

            occurrence=recurrence_form.save(commit=False)
            occurrence.event=event

            if occurrence.end_time<=occurrence.start_time:
                occurrence.end_time=occurrence.get_endtime()
            recurrence_form = recurrence_form_class(instance=occurrence)#to keeo calculated end time if conflict

#this seems to not refresh conflict items, for some reason
            if ("check" in request.POST):#will this run if not saved yet?
                figurehead_conflict=occurrence.figurehead_conflict()
                if figurehead_conflict:
                    conflict["figurehead_conflict"]=figurehead_conflict
                participant_conflict=occurrence.participant_conflict()
                if participant_conflict:
                    conflict["participant_conflict"]=participant_conflict
                blackout_conflict=occurrence.blackout_conflict()
                if blackout_conflict:
                    conflict["blackout_conflict"]=blackout_conflict
                if len(conflict)<=0:
                    conflict_free=True

            if ("save" in request.POST):
                event.save()
                occurrence.event=event
                occurrence.save()
                save_success=True#this doesn't d anyhting, I'm not able to pass it on unless I change the url
                return redirect('swingtime-occurrence', occurrence.event.id,occurrence.id)#important, otherwise can make new ones forever and think editing same one
            # elif "recheck" in request.POST:
            #     dstr_str=request.POST['start_time_0_year']+"-"+request.POST['start_time_0_month']+"-"+request.POST['start_time_0_day']+"T"+request.POST['start_time_1']
            #     locstr=str(request.GET['location'])
            #     url_str='?dtstart=%s&location=%s'%(dstr_str,locstr)
                # if "training" in request.GET and request.GET['training'] not in ["",u'',None,"None"]:
                #     tpk=str(request.GET['training'])
                #     url_str+="&training=%s"%(tpk)
                # elif "training" in request.POST and request.POST['training'] not in ["",u'',None,"None"]:
                #     tpk=str(request.POST['training'])
                #     url_str+="&training=%s"%(tpk)
                #
                # if "challenge" in request.GET and request.GET['challenge'] not in ["",u'',None,"None"]:
                #     cpk=str(request.GET['challenge'])
                #     url_str+="&challenge=%s"%(cpk)
                # elif "challenge" in request.POST and request.POST['challenge'] not in ["",u'',None,"None"]:
                #     cpk=str(request.POST['challenge'])
                #     url_str+="&challenge=%s"%(cpk)

                # return HttpResponseRedirect(url_str)

    # #this happens regardless of post or not
    return render(request,template,
        {'conflict_free':conflict_free,'conflict':conflict,'save_success':save_success,'dtstart': dtstart, 'event_form': event_form, 'single_occurrence_form': recurrence_form})


#-------------------------------------------------------------------------------
@login_required
def _datetime_view(
    request,
    template,
    dt,
    timeslot_factory=None,
    items=None,
    params=None
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
        con=Con.objects.get(start__lte=dt, end__gte=dt)
        locations=con.get_locations()
    except ObjectDoesNotExist:
        con=None
        locations=[]

    return render(request, template, {
        'day':       dt,
        'con':       con,
        'locations': locations,
        'maxwidth': 99/(len(locations)+1),
        'next_day':  dt + timedelta(days=+1),
        'prev_day':  dt + timedelta(days=-1),
        'timeslots': timeslot_factory(dt=dt, items=items, **params)
    })


#-------------------------------------------------------------------------------
@login_required
def day_view(request, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    dt = datetime(int(year), int(month), int(day))
    return _datetime_view(request, template, dt, **params)


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
