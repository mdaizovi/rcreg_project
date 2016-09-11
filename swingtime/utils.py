'''
Common features and functions for swingtime
'''
import calendar
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from dateutil import rrule
import itertools

from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.utils.encoding import python_2_unicode_compatible
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse,resolve


from swingtime.conf import settings as swingtime_settings
from con_event.models import (Con, LOCATION_CATEGORY, LOCATION_TYPE,
        LOCATION_TYPE_FILTER, LOCATION_CATEGORY_FILTER
        )
from scheduler.models import Location


#-------------------------------------------------------------------------------
def html_mark_safe(func):
    '''
    Decorator for functions return strings that should be treated as template
    safe.

    '''
    def decorator(*args, **kws):
        return mark_safe(func(*args, **kws))
    return decorator


#-------------------------------------------------------------------------------
def time_delta_total_seconds(time_delta):
    '''
    Calculate the total number of seconds represented by a
    ``datetime.timedelta`` object

    '''
    return time_delta.days * 3600 + time_delta.seconds


#-------------------------------------------------------------------------------
def month_boundaries(dt=None):
    '''
    Return a 2-tuple containing the datetime instances for the first and last
    dates of the current month or using ``dt`` as a reference.

    '''
    dt = dt or date.today()
    wkday, ndays = calendar.monthrange(dt.year, dt.month)
    start = datetime(dt.year, dt.month, 1)
    return (start, start + timedelta(ndays - 1))


#-------------------------------------------------------------------------------
def default_css_class_cycler():
    return itertools.cycle(('evt-even', 'evt-odd'))


#-------------------------------------------------------------------------------
def css_class_cycler():

    '''
    Return a dictionary keyed by ``EventType`` abbreviations, whose values are an
    iterable or cycle of CSS class names.

    '''
    FMT = 'evt-{0}-{1}'.format
    return defaultdict(default_css_class_cycler, (
        ("", itertools.cycle((FMT("", 'even'), FMT("", 'odd'))))
        for e in []
    ))

#===============================================================================
@python_2_unicode_compatible
class BaseOccurrenceProxy(object):
    '''
    A simple wrapper class for handling the presentational aspects of an
    ``Occurrence`` instance.

    '''
    #---------------------------------------------------------------------------
    def __init__(self, occurrence, col):

        self.column = col
        self._occurrence = occurrence
        self.event_class = ''

    #---------------------------------------------------------------------------
    def __getattr__(self, name):

        return getattr(self._occurrence, name)

    #---------------------------------------------------------------------------
    def __str__(self):

        return self.name


#===============================================================================
@python_2_unicode_compatible
class DefaultOccurrenceProxy(BaseOccurrenceProxy):

    #CONTINUATION_STRING = '^^'
    CONTINUATION_STRING = None  # So can merge rows of activities

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kws):
        super(DefaultOccurrenceProxy, self).__init__(*args, **kws)
        rowspan=1
        link = '<a href="%s">%s</a>' % (
            self.get_absolute_url(),
            #self.title
            self.name
        )

        self._str = itertools.chain(
            (link,),
            itertools.repeat(self.CONTINUATION_STRING)
        )

    #---------------------------------------------------------------------------
    @html_mark_safe
    def __str__(self):
        return next(self._str)


#-------------------------------------------------------------------------------
def create_timeslot_table(
    dt=None,
    items=None,
    loc_id=None,
    lcat=None,
    ltype=None,
    start_time=swingtime_settings.TIMESLOT_START_TIME,
    end_time_delta=swingtime_settings.TIMESLOT_END_TIME_DURATION,
    time_delta=swingtime_settings.TIMESLOT_INTERVAL,
    min_columns=swingtime_settings.TIMESLOT_MIN_COLUMNS,
    css_class_cycles=css_class_cycler,
    proxy_class=DefaultOccurrenceProxy
):
    '''
    Create a grid-like object representing a sequence of times (rows) and
    columns where cells are either empty or reference a wrapper object for
    event occasions that overlap a specific time slot.

    Currently, there is an assumption that if an occurrence has a ``start_time``
    that falls with the temporal scope of the grid, then that ``start_time`` will
    also match an interval in the sequence of the computed row entries.

    * ``dt`` - a ``datetime.datetime`` instance or ``None`` to default to now
    * ``items`` - a queryset or sequence of ``Occurrence`` instances. If
      ``None``, default to the daily occurrences for ``dt``
    * ``start_time`` - a ``datetime.time`` instance
    * ``end_time_delta`` - a ``datetime.timedelta`` instance
    * ``time_delta`` - a ``datetime.timedelta`` instance
    * ``min_column`` - the minimum number of columns to show in the table
    * ``css_class_cycles`` - if not ``None``, a callable returning a dictionary
      keyed by desired ``EventType`` abbreviations with values that iterate over
      progressive CSS class names for the particular abbreviation.
    * ``proxy_class`` - a wrapper class for accessing an ``Occurrence`` object.
      This class should also expose ``event_type`` and ``event_type`` attrs, and
      handle the custom output via its __unicode__ method.

    '''
    from swingtime.models import Occurrence
    dt = dt or datetime.now()
    start_time = start_time.replace(tzinfo=dt.tzinfo) if not start_time.tzinfo else start_time
    dtstart = datetime.combine(dt.date(), start_time)
    dtend = dtstart + end_time_delta

    try:
        con = Con.objects.get(start__lte=dt, end__gte=dt)
        if loc_id:
            locations = [Location.objects.get(pk=int(loc_id))]
        elif lcat or ltype:
            venues = list(con.venue.all())
            if lcat and int(lcat) < len(LOCATION_CATEGORY_FILTER):
                ind = int(lcat)
                loc_cat = LOCATION_CATEGORY_FILTER[ind][1]
                base_q = Location.objects.filter(
                        venue__in=venues,
                        location_category__in=loc_cat
                        )
            elif ltype and int(ltype)<len(LOCATION_TYPE_FILTER):
                ind = int(ltype)
                loc_type = LOCATION_TYPE_FILTER[ind][1]
                base_q = Location.objects.filter(
                        venue__in=venues,
                        location_type__in=loc_type
                        )
            else:
                base_q = Location.objects.filter(venue__in=venues)
            locations = list(base_q)
        else:
            locations = con.get_locations()
    except ObjectDoesNotExist:
        con=None
        locations=[]

    if isinstance(items, QuerySet):
        items = items._clone()
    elif not items:
        items = Occurrence.objects.daily_occurrences(dt)

    # build a mapping of timeslot "buckets"
    timeslots = {}
    n = dtstart
    while n <= dtend:
        timeslots[n] = {}
        n += time_delta

    # fill the timeslot buckets with occurrence proxies
    for item in sorted(items):
        if item.end_time <= dtstart:
            # this item began before the start of our schedle constraints
            continue

        if item.start_time > dtstart:
            rowkey = current = item.start_time
        else:
            rowkey = current = dtstart

        timeslot = timeslots.get(rowkey, None)

        if timeslot is None:
            # TODO fix atypical interval boundry spans
            # This is rather draconian, we should probably try to find a better
            # way to indicate that this item actually occurred between 2 intervals
            # and to account for the fact that this item may be spanning cells
            # but on weird intervals
            continue

        colkey = int(item.location.pk)
        if colkey not in timeslot:
            proxy = proxy_class(item, colkey)
            timeslot[colkey] = proxy

            while current < item.end_time:
                rowkey = current
                row = timeslots.get(rowkey, None)
                if row is None:
                    break

                # we might want to put a sanity check in here to ensure that
                # we aren't trampling some other entry, but by virtue of
                # sorting all occurrence that shouldn't happen
                row[colkey] = proxy
                current += time_delta

    # Determine the number of timeslot columns we should show
    column_lens = [len(x) for x in timeslots.values()]
    if con and locations:
        column_count=len(locations)
        column_range = [int(l.id) for l in locations]
    else:
        column_count = max((min_columns, max(column_lens) if column_lens else 0))
        column_range = range(column_count)
    empty_columns = ['' for x in column_range]

    if css_class_cycles:  # Necessary to make bix box of long events
        column_classes = dict([(i, css_class_cycles()) for i in column_range])
    else:
        column_classes = None

    # Create the chronological grid layout
    table = []
    val_list=timeslots.values()
    prox_obj_list=[]
    prox_obj_unique=[]
    for dic in val_list:
        for obj in dic.values():
            prox_obj_list.append(obj)
            if obj not in prox_obj_unique:
                prox_obj_unique.append(obj)
    for obj in prox_obj_unique:
        obj.rowspan = prox_obj_list.count(obj)

    included_objs = []
    for rowkey in sorted(timeslots.keys()):
        # rowkey is the datetime object within range for day
        cols = empty_columns[:]

        for colkey in column_range:
            # colkey is a dict w/ k,v of {column: object}
            if colkey in timeslots[rowkey].keys():
                proxy = timeslots[rowkey][colkey]
                # So can merge rows of activities
                if proxy and proxy not in included_objs:
                    included_objs.append(proxy)
                    index=column_range.index(colkey)
                    cols[index] = proxy

                    if not proxy.event_class and column_classes:
                        proxy.event_class = next(column_classes[colkey][proxy])
            else:
                index = column_range.index(colkey)
                str1 = "<a href='/events/add/?dtstart="
                str2 = str(rowkey.isoformat())
                str3 = "&location="+str(colkey)
                str4 = "'>+</a>"

                full_str = str1 + str2 + str3 + str4
                cols[index] = str(full_str)

        table.append((rowkey, cols))

    return table
