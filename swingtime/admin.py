try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:
    from django.contrib.contenttypes.generic import GenericTabularInline

from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin,ImportExportActionModelAdmin
from swingtime.models import *

#===============================================================================
# class EventTypeAdmin(admin.ModelAdmin):
#     list_display = ('label', 'abbr')
#

#===============================================================================
class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 1


#===============================================================================
class EventAdmin(admin.ModelAdmin):#No import/export
    list_display = ('training','challenge')
    list_display_links = list_display#makes everything in list display clickable to get to object
    #list_filter = ('event_type', )
    search_fields = ('training__name','challenge__name')
    inlines = [OccurrenceInline]

#===============================================================================
class OccurrenceResource(resources.ModelResource):
    class Meta:
        model = Occurrence
        fields = ('start_time','end_time','event','event__training','event__challenge','location__abbrv')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('event',)
        skip_unchanged = True
        report_skipped = True

#===============================================================================
class OccurrenceAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
#class OccurrenceAdmin(admin.ModelAdmin):No import/export
    list_display = ('event','start_time','end_time','location')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('event__training__name','event__challenge__name','location__name')
    #fields = [field.name for field in Occurrence._meta.fields if field.name != "id"]
    #i think can't get event in admin because editable=False in models
    resource_class = OccurrenceResource



#admin.site.register(Event, EventAdmin)
admin.site.register(Occurrence, OccurrenceAdmin)
#admin.site.register(EventType, EventTypeAdmin)
