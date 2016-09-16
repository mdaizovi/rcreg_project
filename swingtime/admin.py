import datetime

try:
    from django.contrib.contenttypes.admin import GenericTabularInline
except ImportError:
    from django.contrib.contenttypes.generic import GenericTabularInline

from django.contrib import admin
from django.core.urlresolvers import reverse, resolve

from import_export import resources,fields
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from swingtime.models import Occurrence, TrainingRoster


#===============================================================================
class TrainingRosterREGInline(admin.TabularInline):

    model = TrainingRoster
    fk_name = "registered"
    extra = 0
    max_num = 0
    view_on_site = False
    fields = (('intl', 'skill', 'cap'), 'participants')
    filter_horizontal = ('participants',)


#===============================================================================
class TrainingRosterAUDInline(admin.TabularInline):
    model = TrainingRoster
    fk_name = "auditing"
    extra = 0
    max_num = 0
    view_on_site = False
    fields = (('intl', 'skill', 'cap'), 'participants')
    filter_horizontal = ('participants',)


#===============================================================================
class OccurrenceInline(admin.TabularInline):
    model = Occurrence
    extra = 0
    max_num = 0
    view_on_site = False

#===============================================================================
class OccurrenceResource(resources.ModelResource):

    day = fields.Field()
    start = fields.Field()
    end = fields.Field()
    skill_display = fields.Field()
    con_display = fields.Field()
    figureheads = fields.Field()
    coach_real_name = fields.Field()
    description = fields.Field()
    name_with_data = fields.Field()
    gcal_location = fields.Field()
    score = fields.Field()

    #---------------------------------------------------------------------------
    def dehydrate_gcal_location(self,occurrence):

        activity = occurrence.get_activity()
        loc = ""
        if activity and activity.is_a_training():
            loc = activity.figurehead_display
        elif activity and activity.is_a_challenge():
            loc = occurrence.location.name

        return loc

    #---------------------------------------------------------------------------
    def dehydrate_score(self,occurrence):
        activity = occurrence.get_activity()
        score = ""
        if activity and activity.is_a_challenge():
            if activity.roster1score and activity.roster2score:
                score = "%s - %s" % (str(activity.roster1score), str(activity.roster2score))
        return score

    #---------------------------------------------------------------------------
    def dehydrate_name_with_data(self,occurrence):
        """presents data in the way RC is accustomed for gcal import."""

        activity = occurrence.activity
        desc = ""

        if activity:
            skill_text = activity.skill_display().replace("ABCD", "ALL")

            if activity.is_a_training():
                desc += activity.name
                if hasattr(occurrence,'registered') or hasattr(occurrence,'auditing'):
                    if occurrence.registered.intl or occurrence.auditing.intl:
                        desc += " INTL "
                if activity.onsk8s:
                    desc += " (%s" % (skill_text)
                    if not activity.contact:
                        desc += " [NO Contact]"
                    desc += ")"

            elif activity.is_a_challenge():
                gender_display = activity.gender_display().replace("NA/Coed", "Co-ed")
                desc += "%s (%s [%s])" % (activity.name, skill_text,gender_display)

        return desc

    #---------------------------------------------------------------------------
    def dehydrate_skill_display(self,occurrence):

        activity = occurrence.get_activity()
        if activity:
            return activity.skill_display()
        else:
            return ""

    #---------------------------------------------------------------------------
    def dehydrate_con_display(self,occurrence):

        activity = occurrence.activity
        if activity:
            return "%s %s" % (activity.con.year, activity.con.city)
        else:
            return ""

    #---------------------------------------------------------------------------
    def dehydrate_day(self,occurrence):

        fmt = occurrence.start_time.date().strftime("%m/%d/%Y")

        return fmt

    #---------------------------------------------------------------------------
    def dehydrate_start(self,occurrence):

        d = occurrence.start_time

        return d.strftime("%I:%M %p")

    #---------------------------------------------------------------------------
    def dehydrate_end(self,occurrence):

        d = occurrence.end_time

        return d.strftime("%I:%M %p")

    #---------------------------------------------------------------------------
    def dehydrate_figureheads(self,occurrence):

        activity = occurrence.activity
        if activity:
            return activity.figurehead_display
        else:
            return ""

    #---------------------------------------------------------------------------
    def dehydrate_coach_real_name(self,occurrence):
        real_names = ""

        activity = occurrence.activity
        if activity and activity.is_a_training:
            regs = activity.get_figurehead_registrants()
            for r in regs:
                real_names += r.realname+", "
            real_names = real_names[:-2]

        return real_names


    #---------------------------------------------------------------------------
    def dehydrate_description(self, occurrence):

        activity = occurrence.activity
        desc = ""
        if activity and activity.is_a_training():
            desc = activity.full_description()
        elif (activity and activity.is_a_challenge() and
                activity.roster1 and activity.roster1.captain and
                activity.roster2 and activity.roster2.captain
                ):
            # Hoo boy. I'm sorry for this. It's what they want.
            desc += "%s" % (activity.roster1.name)
            if activity.roster1.color:
                desc += " (%s)" % (activity.roster1.color)
            desc += " %s\n" % (activity.roster1.captain.name)
            desc += "%s" % (activity.roster2.name)
            if activity.roster2.color:
                desc += " (%s)" % (activity.roster2.color)
            desc += " %s\n" % (activity.roster2.captain.name)

            desc += "\n*This schedule placement is tentative and subject to "
            desc += "change until the final schedule is released in the summer."
            desc += "\n\nInformation about this challenge, including roster "
            desc += "submission deadlines and procedures: http://tinyurl.com/RC-captain-info"
            desc += "\n\nRollerCon events are scheduled in Pacific Standard Time"
            desc += ", but your google calendar might change it to your timezone."
            desc += "\nhttp://www.timeanddate.com/worldclock/converter.html.\nIf "
            desc += "you want it to show in your google calendar, you can go to "
            desc += "the calendar here: http://rollercon.com/events/  Find the "
            desc += "event, click to expand it, then click the link that says "
            desc += "'copy to my calendar.' "

        return desc

    #---------------------------------------------------------------------------
    class Meta:

        model = Occurrence
        fields = ('day', 'start', 'end', 'training__name', 'challenge__name',
                'name_with_data', 'figureheads', 'coach_real_name',
                'skill_display', 'location__abbrv', 'con_display', 'score',
                'description', 'gcal_location'
                )
        export_order = fields
        skip_unchanged = True
        report_skipped = True

#===============================================================================
class OccurrenceAdmin(ImportExportModelAdmin):

    list_display = ('training', 'challenge', 'start_time', 'end_time', 'location')
    list_display_links = list_display
    search_fields = ('training__name', 'challenge__name', 'location__name')
    fields = (('start_time', 'end_time'), ('training', 'challenge'), 'location')
    resource_class = OccurrenceResource
    inlines = [TrainingRosterREGInline, TrainingRosterAUDInline]

    #---------------------------------------------------------------------------
    def get_formsets(self, request, obj=None):

        for inline in self.get_inline_instances(request, obj):
            if obj and not obj.training:
                continue
            else:
                pass
            yield inline.get_formset(request, obj)

#===============================================================================
class TrainingRosterAdmin(admin.ModelAdmin):

    list_display = ('__str__','cap','intl')
    list_display_links = list_display
    search_fields = ('registered__training__name', 'auditing__training__name')
    fields = (('intl', 'cap'), 'participants', ('registered', 'auditing'))
    view_on_site = False
    filter_horizontal = ('participants',)

    #---------------------------------------------------------------------------
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        try:  # So will still work when making a new one
            object_id = resolve(request.path).args[0]
            if object_id:
                troster = TrainingRoster.objects.get(pk=object_id)
                if (troster.registered and troster.registered.training and
                        troster.registered.training.con
                        ):
                    con = troster.registered.training.con
                elif (troster.auditing and troster.auditing.training and
                        troster.auditing.training.con
                        ):
                    con = troster.auditing.training.con

                if con and db_field.name == "participants":
                    kwargs["queryset"] = Registrant.objects.filter(
                            pass_type__in=['MVP', 'Skater'],
                            con=con
                            )
        except:
            pass
        return super(TrainingRosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(Occurrence, OccurrenceAdmin)
admin.site.register(TrainingRoster, TrainingRosterAdmin)
