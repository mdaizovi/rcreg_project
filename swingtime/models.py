from datetime import datetime, date, timedelta
from dateutil import rrule

from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.utils.dateparse import parse_datetime,parse_time
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import connection as dbconnection
#print "dbc0:", len(dbconnection.queries)
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
#from con_event.models import Con
from scheduler.models import Location, Challenge, Training,INTEREST_RATING
from con_event.models import Blackout,Registrant

try:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation

from swingtime.conf import settings as swingtime_settings

#####NOTE to self (Dahmer):
#temporarily got rid of Note, description field.
#am thinking of getitng rid of title and Event type.
#title is probably okay as long as I keep funciton to return chal or training
#only get rid of event type if you know you'll never want to use the css helper function.
#either way, need to resolve either of these in utils if get rid of them/


__all__ = (
    #'EventType',
    'Event',
    'Occurrence',
    #'create_event'
)


#===============================================================================
@python_2_unicode_compatible
class EventType(models.Model):
    '''
    Simple ``Event`` classifcation.
    '''
    abbr = models.CharField(_('abbreviation'), max_length=4, unique=True)
    label = models.CharField(_('label'), max_length=50)

    #===========================================================================
    class Meta:
        verbose_name = _('event type')
        verbose_name_plural = _('event types')

    #---------------------------------------------------------------------------
    def __str__(self):
        return self.label


#===============================================================================

@python_2_unicode_compatible
class Event(models.Model):
    '''
    Container model for general metadata and associated ``Occurrence`` entries.
    '''
    #title = models.CharField(_('title'), max_length=32,null=True,blank=True)
    #event_type = models.ForeignKey(EventType, verbose_name=_('event type'),null=True,blank=True)

    training=models.ForeignKey(Training,null=True,blank=True,on_delete=models.SET_NULL)
    challenge=models.ForeignKey(Challenge,null=True,blank=True,on_delete=models.SET_NULL)

    #===========================================================================
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        #ordering = ('title', )

    #---------------------------------------------------------------------------
    def get_activity(self):
        '''
        Dahmer custom. Returns training or activity related to Event.
        '''
        if self.training:
            activity=self.training
        elif self.challenge:
            activity=self.challenge
        else:
            activity=None
        return activity

    #---------------------------------------------------------------------------
    def __str__(self):
        activity=self.get_activity()
        if activity:
            return activity.name
        else:
            return "no challenge or training yet"

    #---------------------------------------------------------------------------
    # @models.permalink
    # def get_absolute_url(self):
    #     return ('swingtime-event', [str(self.id)])

    #---------------------------------------------------------------------------
    # def add_occurrences(self, start_time, end_time, **rrule_params):
    #     '''
    #     Add one or more occurences to the event using a comparable API to
    #     ``dateutil.rrule``.
    #
    #     If ``rrule_params`` does not contain a ``freq``, one will be defaulted
    #     to ``rrule.DAILY``.
    #
    #     Because ``rrule.rrule`` returns an iterator that can essentially be
    #     unbounded, we need to slightly alter the expected behavior here in order
    #     to enforce a finite number of occurrence creation.
    #
    #     If both ``count`` and ``until`` entries are missing from ``rrule_params``,
    #     only a single ``Occurrence`` instance will be created using the exact
    #     ``start_time`` and ``end_time`` values.
    #     '''
    #     count = rrule_params.get('count')
    #     until = rrule_params.get('until')
    #     if not (count or until):
    #         self.occurrence_set.create(start_time=start_time, end_time=end_time)
    #     else:
    #         rrule_params.setdefault('freq', rrule.DAILY)
    #         delta = end_time - start_time
    #         occurrences = []
    #         for ev in rrule.rrule(dtstart=start_time, **rrule_params):
    #             occurrences.append(Occurrence(start_time=ev, end_time=ev + delta, event=self))
    #         self.occurrence_set.bulk_create(occurrences)

    #---------------------------------------------------------------------------
    # def upcoming_occurrences(self):
    #     '''
    #     Return all occurrences that are set to start on or after the current
    #     time.
    #     '''
    #     return self.occurrence_set.filter(start_time__gte=datetime.now())

    #---------------------------------------------------------------------------
    # def next_occurrence(self):
    #     '''
    #     Return the single occurrence set to start on or after the current time
    #     if available, otherwise ``None``.
    #     '''
    #     upcoming = self.upcoming_occurrences()
    #     return upcoming[0] if upcoming else None

    #---------------------------------------------------------------------------
    # def daily_occurrences(self, dt=None):
    #     '''
    #     Convenience method wrapping ``Occurrence.objects.daily_occurrences``.
    #     '''
    #     return Occurrence.objects.daily_occurrences(dt=dt, event=self)
    #
    # def validate_unique(self, *args, **kwargs):#this probably shouldn't be validate unique, some other validate
    #     if self.training and self.challenge:
    #         raise ValidationError({
    #             NON_FIELD_ERRORS: ["Event cannot be BOTH a Challenge and a Training",],})
    #
    #     if not self.training and not self.challenge:
    #         raise ValidationError({
    #             NON_FIELD_ERRORS: ["Please choose either a Challenge or Training",],})


#===============================================================================
class OccurrenceManager(models.Manager):

    use_for_related_fields = True

    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None):
    #def daily_occurrences(self, dt=None, event=None):
        '''
        Returns a queryset of for instances that have any overlap with a
        particular day.

        * ``dt`` may be either a datetime.datetime, datetime.date object, or
          ``None``. If ``None``, default to the current day.

        * ``event`` can be an ``Event`` instance for further filtering.
        '''
        dt = dt or datetime.now()
        start = datetime(dt.year, dt.month, dt.day)
        end = start.replace(hour=23, minute=59, second=59)
        qs = self.filter(
            models.Q(
                start_time__gte=start,
                start_time__lte=end,
            ) |
            models.Q(
                end_time__gte=start,
                end_time__lte=end,
            ) |
            models.Q(
                start_time__lt=start,
                end_time__gt=end
            )
        )

        #return qs.filter(event=event) if event else qs
        return qs


#===============================================================================
@python_2_unicode_compatible
class Occurrence(models.Model):
    '''
    Represents the start end time for a specific occurrence of a master ``Event``
    object.
    '''
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'))
    #delete field eventually, when it feels safe
    event = models.ForeignKey(Event, verbose_name=_('event'),null=True, blank=True,on_delete=models.SET_NULL)
    #Why did i say null=true for locaiton? prob so occurrance doesn't get deleted if locaiton does
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    interest=models.IntegerField(null=True, blank=True,choices=INTEREST_RATING)

    training=models.ForeignKey(Training,null=True,blank=True,on_delete=models.SET_NULL)
    challenge=models.ForeignKey(Challenge,null=True,blank=True,on_delete=models.SET_NULL)

    objects = OccurrenceManager()

    #===========================================================================
    class Meta:
        verbose_name = _('occurrence')
        verbose_name_plural = _('occurrences')
        ordering = ('start_time', 'end_time')

    #---------------------------------------------------------------------------
    def __str__(self):
        #return '{}: {}'.format(self.title, self.start_time.isoformat())
        return '{}: {}'.format(self.name, self.start_time.isoformat())

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-occurrence', [str(self.id)])

    #---------------------------------------------------------------------------
    def __lt__(self, other):
        return self.start_time < other.start_time

    #---------------------------------------------------------------------------
    # @property
    # def title(self):
    #     activity=self.event.get_activity()
    #     if activity:
    #         return activity.name
    #     else:
    #         return "no challenge or training chosen"
    #---------------------------------------------------------------------------

#############practicing before deleting
    # @property
    # def event_type(self):
    #     return self.event.event_type

    #---------------------------------------------------------------------------
    def get_activity(self):
        '''
        Dahmer custom. Returns training or activity related to Event.
        Currently written to ease the transition to not having Event as a model
        '''
        activity=None
        if hasattr(self, 'event'):
            if self.event:
                activity=self.event.get_activity()
        if not activity:#either bc no attr, or no activity

            if self.training or self.challenge:
                if self.training:
                    activity=self.training
                elif self.challenge:
                    activity=self.challenge

        return activity
    #---------------------------------------------------------------------------
#######eventually I want this to replace event model, just being cautious######################
    @property
    def activity(self):
    #def event(self): #change to this somedaty?
        return self.get_activity()


    #---------------------------------------------------------------------------
########eventually I want this to replace title######################
    @property
    def name(self):
        activity=self.get_activity()

        if activity and activity.name:
            return activity.name
        else:
            if self.interest:
                temp_name="Empty (Interest: "+str(self.interest)+")"
            else:
                temp_name="Empty"
            return temp_name
    #---------------------------------------------------------------------------

    #reference: http://stackoverflow.com/questions/7366363/adding-custom-django-model-validation

    def validate_unique(self, *args, **kwargs):
        super(Occurrence, self).validate_unique(*args, **kwargs)

        if self.start_time and self.end_time and self.location:

            qs = self.__class__._default_manager.filter(
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
                location=self.location)

            if not self._state.adding and self.pk is not None:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    NON_FIELD_ERRORS: ["You can't have more than 1 occurrence in the same place at the same time",],})

        if self.training and self.challenge:#can't add until occurrence has training and challenge
            raise ValidationError({
                NON_FIELD_ERRORS: ["Occurrence cannot be BOTH a Challenge and a Training",],})



    #---------------------------------------------------------------------------
    def get_endtime(self):
        """Dahmer custom funct to get end time based on the train/chal it's linked to,
        and pad an extra 15 mins for 30 min chal or 30 mins for 90 min chal
        REQUIRES event and start time"""
        duration=1#default, may be overridden
        activity=self.get_activity()
        if activity and activity.duration:
            duration=float(activity.duration)

        dur_delta=int(duration*60)
        end_time=self.start_time+timedelta(minutes=dur_delta)
        return end_time
    #---------------------------------------------------------------------------
    def get_initial_interest(self,start_time):
        """Figures out intiial interest level based on when event is occurring.
        Start time is fed so can be calculated for initial before any other data is populated."""
        pass


    #---------------------------------------------------------------------------
    def figurehead_conflict(self):
        """Dahmer custom function. Checks to see if any Event figureheads (coach, captain) are participating in other occurrances at same time.
        If so, returns dict w/  activity k, skater list v, but has no teeth, can be overridden, is just an FYI warning"""
        activity=self.get_activity()#0db hits
        figureheads=[]
        conflict_dict={}
        if activity:
            figureheads=activity.get_figurehead_registrants()#figureheads is for getting blackouts, but where to put the logic?
        else:
            figureheads=[]

        #0 db hits
        #concurrent=Occurrence.objects.filter(start_time__lt=self.end_time,end_time__gt=self.start_time).exclude(pk=self.pk).select_related('challenge').select_related('training')
        #adding a half hour padding:
        concurrent=Occurrence.objects.filter(start_time__lt=(self.end_time + timedelta(minutes=30)),end_time__gt=(self.start_time - timedelta(minutes=30))).exclude(pk=self.pk).select_related('challenge').select_related('training')

        for o in concurrent:
            event_activity=o.get_activity()
            if event_activity: #could be an empty timeslot
                event_part=event_activity.participating_in()
                conflict=set(figureheads).intersection(event_part)
                if len( conflict ) > 0:
                    conflict_dict[event_activity]=list(conflict)

        if len(conflict_dict)>0:
            return conflict_dict
        else:
            return None

    #-------------------------------------------------------------------------------
    def participant_conflict(self):
        """Dahmer custom function. Checks to see if any Event participants are participating in other occurrances at same time.
        If so, returns dict w/  activity k, skater list v, but has no teeth, can be overridden, is just an FYI warning"""
        activity=self.get_activity()
        figureheads=[]
        conflict_dict={}

        if activity:
            occur_part = activity.participating_in()#cut down form 7 to 4 db hits
        else:
            occur_part=[]
        #concurrent=Occurrence.objects.filter(start_time__lt=self.end_time,end_time__gt=self.start_time).exclude(pk=self.pk)
        #adding a half hour padding:
        concurrent=Occurrence.objects.filter(start_time__lt=(self.end_time + timedelta(minutes=30)),end_time__gt=(self.start_time - timedelta(minutes=30))).exclude(pk=self.pk)

        for o in concurrent:
            event_activity=o.get_activity()
            if event_activity: #could be an empty timeslot
                event_part=event_activity.participating_in()
                inter=set(occur_part).intersection(event_part)
                if len( inter ) > 0:
                    conflict_dict[event_activity]=list(inter)
                    #conflict_dict[event_activity]=event_part#whoops, this adds all people, not just the intersection!
        if len(conflict_dict)>0:
            #print "conflict_dict",conflict_dict
            return conflict_dict
        else:
            return None

    #-------------------------------------------------------------------------------
    def blackout_conflict(self):
        """Dahmer custom function. Checks to see if any Event figureheads (coach, captain have blackouts during Occu time.
        If so, returns dict w/  blackout k, skater list v, but has no teeth, can be overridden, is just an FYI warning"""
        #print("running o blackout_conflict")
        activity=self.get_activity()
        figureheads=[]
        conflict_dict={}
        daypart=[]
        #print("activity ",activity)
        if activity:
            figureheads=activity.get_figurehead_registrants()#figureheads is for getting blackouts, but where to put the logic?
        else:
            figureheads=[]

        odate=self.start_time.date()
        if self.start_time.time() >= parse_time('12:00:00'):
            daypart.append("PM")
        else:
            daypart.append("AM")
        if (self.end_time.time() >= parse_time('12:00:00')) and ("PM" not in daypart):
            daypart.append("PM")
        #print("daypart ",daypart)
        for f in figureheads:
            #print("Figurehead ",f)
            potential_bouts=Blackout.objects.filter(registrant=f, date=odate, ampm__in=daypart)
            if len(list(potential_bouts))>0:
                conflict_dict[f]=list(potential_bouts)
        #print("conflict_dict ",conflict_dict)

        if len(conflict_dict)>0:
            return conflict_dict
        else:
            return None
#-------------------------------------------------------------------------------
    def get_add_url(self):
        """Creates string of URL to call add-event page.
        Like a DIY get abdolute url"""

        dstr_str=self.start_time.isoformat()

        url_str='/events/add/?dtstart=%s&location=%s'%(dstr_str,str(self.location.pk))

        if self.training:
            url_str+="&training=%s"%(str(self.training.pk))
        if self.challenge:
            url_str+="&challenge=%s"%(str(self.challenge.pk))

        return url_str

#-------------------------------------------------------------------------------
##Not totally sure I want to do this
# class TrainingRoster(models.Model):
#     gender=models.CharField(max_length=30, choices=GENDER, default=GENDER[0][0])
#     intl=models.NullBooleanField(default=False)
#     participants=models.ManyToManyField(Registrant, blank=True)
#     cap=models.IntegerField(null=True, blank=True)
#
#     #Reminder: can have 1 of these but not both.
#     registered=models.OneToOneField("Occurrence", related_name="registered_O",null=True, blank=True)
#     auditing=models.OneToOneField("Occurrence", related_name="auditing_O",null=True, blank=True)
#
#     def __unicode__(self):
#         return self.name
#
#     # class Meta:
#     #     ordering=('registered__start_time','auditing__start_time','name')
#
#     @property
#     def name(self):
#         if self.registered:
#             return ("REGISTERED: ",self.registered)
#         elif self.auditing:
#             return ("AUDITING: ",self.auditing)
#         else:
#             return "unnamed Training Roster"
#     #---------------------------------------------------------------------------
#     def validate_unique(self, *args, **kwargs):
#         super(TrainingRoster, self).validate_unique(*args, **kwargs)
#         if self.registered and self.auditing:
#             raise ValidationError({
#                 NON_FIELD_ERRORS: ["Roster cannot be both Registered and Auditing",],})
#
#         if not self.registered and not self.auditing:
#             raise ValidationError({
#                 NON_FIELD_ERRORS: ["Please choose a Training Occurrence",],})
