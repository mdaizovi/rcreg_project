try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:
    from django.contrib.contenttypes.generic import GenericTabularInline

from django.contrib import admin
from swingtime.models import *

#===============================================================================
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('label', 'abbr')


#===============================================================================
class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 1


#===============================================================================
class EventNoteInline(GenericTabularInline):
    model = Note
    extra = 1


#===============================================================================
class EventAdmin(admin.ModelAdmin):
    list_display = ('training','challenge')
    #list_filter = ('event_type', )
    search_fields = ('training','challenge')
    inlines = [EventNoteInline, OccurrenceInline]


admin.site.register(Event, EventAdmin)
admin.site.register(EventType, EventTypeAdmin)
