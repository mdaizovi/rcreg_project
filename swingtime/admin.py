try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:
    from django.contrib.contenttypes.generic import GenericTabularInline

from django.contrib import admin
from django.core.urlresolvers import reverse, resolve
from import_export import resources,fields
from import_export.admin import ImportExportModelAdmin,ImportExportActionModelAdmin
#from swingtime.models import *
from swingtime.models import Occurrence,TrainingRoster
import datetime
#import time


class TrainingRosterREGInline(admin.TabularInline):
    model = TrainingRoster
    fk_name = "registered"
    extra = 0
    max_num=0#gets rid of + Another button
    view_on_site = False
    fields=(('intl','skill','cap'),'participants')
    filter_horizontal = ('participants',)

class TrainingRosterAUDInline(admin.TabularInline):
    model = TrainingRoster
    fk_name = "auditing"
    extra = 0
    max_num=0#gets rid of + Another button
    view_on_site = False
    fields=(('intl','skill','cap'),'participants')
    filter_horizontal = ('participants',)

class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 0
    max_num=0#gets rid of + Another button
    view_on_site = False

#===============================================================================
class OccurrenceResource(resources.ModelResource):
    day=fields.Field()
    start=fields.Field()
    end=fields.Field()
    skill_display=fields.Field()
    con_display=fields.Field()
    figureheads=fields.Field()
    description=fields.Field()


    def dehydrate_skill_display(self,occurrence):
        activity=occurrence.get_activity()
        if activity:
            return activity.skill_display()
        else:
            return ""

    def dehydrate_con_display(self,occurrence):
        activity=occurrence.activity
        if activity:
            return "%s %s"%(activity.con.year,activity.con.city)
        else:
            return ""

    def dehydrate_day(self,occurrence):
        return occurrence.start_time.date()

    def dehydrate_start(self,occurrence):
        d=occurrence.start_time
        return d.strftime("%I:%M %p")

    def dehydrate_end(self,occurrence):
        d=occurrence.end_time
        return d.strftime("%I:%M %p")

    def dehydrate_figureheads(self,occurrence):
        activity=occurrence.activity
        if activity:
            return activity.get_figurehead_display()
        else:
            return ""

    def dehydrate_description(self,occurrence):
        activity=occurrence.activity
        # if activity and hasattr(activity, 'description'):
        #     return activity.description
        if activity and activity.is_a_training():
            return activity.full_description()
        else:
            return ""


    class Meta:
        model = Occurrence
        fields = ('day','start','end','training__name','challenge__name','figureheads','skill_display','location__abbrv','con_display','description')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('event',)
        skip_unchanged = True
        report_skipped = True

#===============================================================================
class OccurrenceAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
#class OccurrenceAdmin(admin.ModelAdmin):No import/export
    list_display = ('training','challenge','start_time','end_time','location')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('training__name','challenge__name','location__name')
    #fields = [field.name for field in Occurrence._meta.fields if field.name != "id"]
    #i think can't get event in admin because editable=False in models
    fields = (('start_time','end_time'),('training','challenge'),'location')
    resource_class = OccurrenceResource
    inlines = [TrainingRosterREGInline,TrainingRosterAUDInline]

    def get_formsets(self, request, obj=None):
        #This makes is to it only gets reg/aud inline if it's a training occurrence
        for inline in self.get_inline_instances(request, obj):
            if obj and not obj.training:
                continue
            else:
                pass
            yield inline.get_formset(request, obj)

#===============================================================================
class TrainingRosterAdmin(admin.ModelAdmin):#No import/export
#I might have to jut give ivanna an easy way to make it INTL. This feels like it's going to be messy.
    list_display = ('__str__','cap','intl')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('registered__training__name','auditing__training__name')
    fields = (('intl','cap'),'participants',('registered','auditing'))
    view_on_site = False

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        try:#So will still work when making a new one
            object_id = resolve(request.path).args[0]
            if object_id:
                troster=TrainingRoster.objects.get(pk=object_id)
                if troster.registered and troster.registered.training and troster.registered.training.con:
                    con=troster.registered.training.con
                elif troster.auditing and troster.auditing.training and troster.auditing.training.con:
                    con=troster.auditing.training.con

                if con and db_field.name == "participants":
                    kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=con)
        except:
            pass
        return super(TrainingRosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(Occurrence, OccurrenceAdmin)#Everything I need from this is accomplished in Occurrance inline through the Event.
admin.site.register(TrainingRoster, TrainingRosterAdmin)
