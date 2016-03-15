from datetime import datetime, date, timedelta
from dateutil import rrule

from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
#from con_event.models import Con
from scheduler.models import Location, Challenge, Training

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
    'EventType',
    'Event',
    'Occurrence',
    'create_event'
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

class EventManager(models.Manager):

    #---------------------------------------------------------------------------
    def get_add_url(self):
        """This is me trying to get a str of this link. I fail"""
        #return reverse('swingtime.views.add_event', args=[dt=dt, location=str(location)])
        pass

#===============================================================================

@python_2_unicode_compatible
class Event(models.Model):
    '''
    Container model for general metadata and associated ``Occurrence`` entries.
    '''
    #title = models.CharField(_('title'), max_length=32,null=True,blank=True)
    event_type = models.ForeignKey(EventType, verbose_name=_('event type'),null=True,blank=True)

    training=models.ForeignKey(Training,null=True,blank=True,on_delete=models.SET_NULL)
    challenge=models.ForeignKey(Challenge,null=True,blank=True,on_delete=models.SET_NULL)

    objects = EventManager()

    #===========================================================================
    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        #ordering = ('title', )

    #---------------------------------------------------------------------------
    def __str__(self):
        if self.challenge:
            return self.challenge.name
        elif self.training:
            return self.training.name
        else:
            return "no challenge or training yet"

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-event', [str(self.id)])

    #---------------------------------------------------------------------------
    def add_occurrences(self, start_time, end_time, **rrule_params):
        '''
        Add one or more occurences to the event using a comparable API to
        ``dateutil.rrule``.

        If ``rrule_params`` does not contain a ``freq``, one will be defaulted
        to ``rrule.DAILY``.

        Because ``rrule.rrule`` returns an iterator that can essentially be
        unbounded, we need to slightly alter the expected behavior here in order
        to enforce a finite number of occurrence creation.

        If both ``count`` and ``until`` entries are missing from ``rrule_params``,
        only a single ``Occurrence`` instance will be created using the exact
        ``start_time`` and ``end_time`` values.
        '''
        count = rrule_params.get('count')
        until = rrule_params.get('until')
        if not (count or until):
            self.occurrence_set.create(start_time=start_time, end_time=end_time)
        else:
            rrule_params.setdefault('freq', rrule.DAILY)
            delta = end_time - start_time
            occurrences = []
            for ev in rrule.rrule(dtstart=start_time, **rrule_params):
                occurrences.append(Occurrence(start_time=ev, end_time=ev + delta, event=self))
            self.occurrence_set.bulk_create(occurrences)

    #---------------------------------------------------------------------------
    def upcoming_occurrences(self):
        '''
        Return all occurrences that are set to start on or after the current
        time.
        '''
        return self.occurrence_set.filter(start_time__gte=datetime.now())

    #---------------------------------------------------------------------------
    def next_occurrence(self):
        '''
        Return the single occurrence set to start on or after the current time
        if available, otherwise ``None``.
        '''
        upcoming = self.upcoming_occurrences()
        return upcoming[0] if upcoming else None

    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None):
        '''
        Convenience method wrapping ``Occurrence.objects.daily_occurrences``.
        '''
        return Occurrence.objects.daily_occurrences(dt=dt, event=self)


#===============================================================================
class OccurrenceManager(models.Manager):

    use_for_related_fields = True

    #---------------------------------------------------------------------------
    def daily_occurrences(self, dt=None, event=None):
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

        return qs.filter(event=event) if event else qs


#===============================================================================
@python_2_unicode_compatible
class Occurrence(models.Model):
    '''
    Represents the start end time for a specific occurrence of a master ``Event``
    object.
    '''
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'))
    event = models.ForeignKey(Event, verbose_name=_('event'), editable=False)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)

    objects = OccurrenceManager()

    #===========================================================================
    class Meta:
        verbose_name = _('occurrence')
        verbose_name_plural = _('occurrences')
        ordering = ('start_time', 'end_time')

    #---------------------------------------------------------------------------
    def __str__(self):
        return '{}: {}'.format(self.title, self.start_time.isoformat())

    #---------------------------------------------------------------------------
    @models.permalink
    def get_absolute_url(self):
        return ('swingtime-occurrence', [str(self.event.id), str(self.id)])

    #---------------------------------------------------------------------------
    def __lt__(self, other):
        return self.start_time < other.start_time

    #---------------------------------------------------------------------------
    @property
    def title(self):
        if self.event.challenge:
            return self.event.challenge.name
        elif self.event.training:
            return self.event.training.name
        else:
            return "no challenge or training chosen"


    #---------------------------------------------------------------------------
    @property
    def event_type(self):
        return self.event.event_type

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
                    NON_FIELD_ERRORS: ["You can't have more than 1 event in the same place at the same time",],})

    #---------------------------------------------------------------------------
    def get_endtime(self):
        """Dahmer custom funct to get end time based on the train/chal it's linked to,
        and pad an extra 15 mins for 30 min chal or 30 mins for 90 min chal
        REQUIRES event and start time"""

        padding=0

        if self.event.training:
            duration=float(self.event.training.duration)
        elif self.event.challenge:
            duration=float(self.event.challenge.duration)
            padding=.5*duration#to give a 15 min pad for 30 min chals, or 30 min pad to 60 min chals
            padding=round(padding, 2)
        else:
            duration=1 #default 1 hour?

        dur_delta=int((duration+padding)*60)
        end_time=self.start_time+timedelta(minutes=dur_delta)
        return end_time


    #---------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def create_event(
    #title,
    event_type,
    start_time=None,
    end_time=None,
    **rrule_params
):
    '''
    Convenience function to create an ``Event``, optionally create an
    ``EventType``, and associated ``Occurrence``s. ``Occurrence`` creation
    rules match those for ``Event.add_occurrences``.

    Returns the newly created ``Event`` instance.

    Parameters

    ``event_type``
        can be either an ``EventType`` object or 2-tuple of ``(abbreviation,label)``,
        from which an ``EventType`` is either created or retrieved.

    ``start_time``
        will default to the current hour if ``None``

    ``end_time``
        will default to ``start_time`` plus swingtime_settings.DEFAULT_OCCURRENCE_DURATION
        hour if ``None``

    ``freq``, ``count``, ``rrule_params``
        follow the ``dateutils`` API (see http://labix.org/python-dateutil)

    '''

    if isinstance(event_type, tuple):
        event_type, created = EventType.objects.get_or_create(
            abbr=event_type[0],
            label=event_type[1]
        )

    event = Event.objects.create(
        event_type=event_type
    )

    start_time = start_time or datetime.now().replace(
        minute=0,
        second=0,
        microsecond=0
    )

    end_time = end_time or (start_time + swingtime_settings.DEFAULT_OCCURRENCE_DURATION)
    event.add_occurrences(start_time, end_time, **rrule_params)
    return event
