from django.contrib import admin
from con_event.models import Con,Registrant,Blackout, Country, State,Blog,SKILL_LEVEL, SKILL_LEVEL_SK8R
from import_export import resources
from import_export.admin import ImportExportModelAdmin,ImportExportActionModelAdmin
from django.contrib.auth.models import User
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME
from django.db.models import Q

"""State and Country are not here, no need to edit from admin"""


class CountryAdmin(admin.ModelAdmin):
    list_display= ('name','slugname')
    fields=('name','slugname')

class StateAdmin(admin.ModelAdmin):
    list_display= ('name','slugname','country')
    fields= ('name','slugname','country')

class ConAdmin(admin.ModelAdmin):
    list_display= ('city','start','end')
    fields=(('city','state','country'),('venue'),('start','end'),
        ('challenge_submission_start','training_submission_end'),('sched_visible','sched_final'),
        ('hoursb4signup','morning_class_cutoff','dayb4signup_start'),
        ('BPT_event_id','ticket_link','hotel_book_link'))

class RegistrantResource(resources.ModelResource):

    class Meta:
        model = Registrant
        fields = ('id','BPT_Ticket_ID','state','country','pass_type','last_name','first_name','email','sk8name','sk8number',
            'skill','gender','affiliation','ins_carrier','ins_number','age_group','volunteer','favorite_part',
            'intl','con','con__city','con__year')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('id','state','country','con')
        skip_unchanged = True
        report_skipped = True


class RegistrantAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
#class RegistrantAdmin(ImportExportActionModelAdmin):#This puts the export button with the Action thing, where you delete. DANGER easy to almost delete
    list_display= ('con','first_name','last_name','sk8name','sk8number','pass_type','gender','skill','intl')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('first_name', 'last_name','sk8name','sk8number','email',"con__year", 'con__city')
    fields = (('con','pass_type'),('first_name','last_name','email'),('sk8name','sk8number'),('skill','gender','intl'),'user',('country','state'),'captaining',
        ('BPT_Ticket_ID','affiliation','ins_carrier','ins_number','age_group','favorite_part','volunteer'),'internal_notes')
    list_filter = ('con', 'pass_type','gender')
    resource_class = RegistrantResource

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_SK8R
        return super(RegistrantAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)


class BlackoutResource(resources.ModelResource):

    class Meta:
        model = Blackout
        fields = ('id','registrant','date','ampm')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        skip_unchanged = True
        report_skipped = True

class BlackoutAdmin(ImportExportModelAdmin):

    list_display = ('registrant','date','ampm')
    fields = ('registrant','date','ampm')

class BlogResource(resources.ModelResource):

    class Meta:
        model = Blog
        fields = ('id','headline','slugname','date','user','post')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('user')
        skip_unchanged = True
        report_skipped = True

class BlogAdmin(ImportExportModelAdmin):
    list_display= ('headline', 'date',)
    exclude=('slugname',)
    view_on_site = True
    #https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.admin.ModelAdmin.formfield_for_foreignkey
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:#So will still work when making a new one
            if db_field.name == "user":
                kwargs["queryset"] = User.objects.filter(Q(groups__name__in=[BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME])|Q(is_staff=True))
            return super(BlogAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        except:
            pass


admin.site.register(State, StateAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(Con, ConAdmin)
admin.site.register(Registrant, RegistrantAdmin)
admin.site.register(Blackout, BlackoutAdmin)
admin.site.register(Blog, BlogAdmin)
