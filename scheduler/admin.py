#scheduler admin
from con_event.models import Con,Registrant, SKILL_LEVEL_TNG,SKILL_LEVEL_CHG,SKILL_LEVEL, SKILL_LEVEL_ACT
from django.contrib import admin
from scheduler.models import Venue, Location, Roster, Challenge, Training, Coach
from import_export import resources
from import_export.admin import ImportExportModelAdmin,ImportExportActionModelAdmin
from django.core.urlresolvers import reverse, resolve
#ImportMixin, ExportMixin, ImportExportMixin
from django import forms
from django.forms import ModelForm

#helpful: http://stackoverflow.com/questions/949268/django-accessing-the-model-instance-from-within-modeladmin


class LocationInline(admin.TabularInline):
#class LocationInline(admin.StackedInline):#looks terrible for this purpose, maybe other model
    model = Location
    fields=('name','location_type')

class VenueAdmin(admin.ModelAdmin):
    list_display= ('name',)
    search_fields = ('name',)

    inlines = [
        LocationInline,
    ]

class LocationAdmin(admin.ModelAdmin):
    list_display= ('venue','name','location_type')
    search_fields = ('venue','name','location_type')


class RegisteredInline(admin.StackedInline):
    model = Roster
    fk_name = "registered"
    fields=(('intl','gender','skill'),'participants')
    filter_horizontal = ('participants',)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_TNG
        return super(RegisteredInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        training_id = resolve(request.path).args[0]
        training=Training.objects.get(pk=training_id)
        if db_field.name == "participants":
            kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=training.con)
        return super(RegisteredInline, self).formfield_for_manytomany(db_field, request, **kwargs)

class AuditingInline(admin.StackedInline):
    model = Roster
    fk_name = "auditing"
    fields=(('intl','gender','skill'),'participants')
    filter_horizontal = ('participants',)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_TNG
        return super(AuditingInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        training_id = resolve(request.path).args[0]
        training=Training.objects.get(pk=training_id)
        if db_field.name == "participants":
            kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater','Offskates'],con=training.con)
        return super(AuditingInline, self).formfield_for_manytomany(db_field, request, **kwargs)

class RosterResource(resources.ModelResource):
    class Meta:
        model = Roster
        fields = ('id','name','captain','captain__sk8name','color','skill','gender','intl','con','con__city','con__year')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('captain','con')
        skip_unchanged = True
        report_skipped = True

class RosterAdmin(ImportExportActionModelAdmin):#This puts the export button with the Action thing, where you delete. DANGER easy to almost delete
    list_display= ('name', 'captain','cap')
    search_fields = ('name', 'captain')
    filter_horizontal = ('participants',)
    list_filter = ('con','skill','gender','intl')
    resource_class = RosterResource

    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        object_id = resolve(request.path).args[0]
        roster=Roster.objects.get(pk=object_id)
        if db_field.name == "captain":
            kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=roster.con)
        return super(RosterAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        object_id = resolve(request.path).args[0]
        roster=Roster.objects.get(pk=object_id)
        if db_field.name == "participants":
            kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=roster.con)
        return super(RosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_ACT#activity bc this could refer to either training or challenge, at this point
        return super(RosterAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)


class ChallengeResource(resources.ModelResource):
    class Meta:
        model = Challenge
        fields = ('id','name','roster1','roster1__name','roster1__captain','roster1__captain__sk8name','captain1accepted','roster1score','roster2','roster2__name','roster2__captain','roster2__captain__sk8name','captain2accepted','roster2score','is_a_game','location_type','RCaccepted','created_on','submitted_on','con','con__city','con__year')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        #I think I don't want to import this one, only export. too compex. don't think I can specify that, though.
        import_id_fields = ('roster1','roster1__captain','roster2','roster2__captain','con')
        skip_unchanged = True
        report_skipped = True

class ChallengeAdmin(ImportExportActionModelAdmin):
    list_display= ('name', 'con')
    search_fields = ('name','roster1__name', 'roster2__name')
    fields = (('con','RCaccepted','RCrejected'),('location_type','duration','ruleset','gametype','is_a_game'),('created_on','submitted_on'),
        ('roster1','captain1accepted','roster1score'),('roster2','captain2accepted','roster2score'))
    list_filter = ('con','location_type','is_a_game')
    resource_class = ChallengeResource

    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        challenge_id = resolve(request.path).args[0]
        challenge=Challenge.objects.get(pk=challenge_id)
        if db_field.name in ["roster1","roster2"]:
            #I could maybe filter by cap as well, to ensure only get game teams? worried i'll forget about that and cause problems.
            kwargs["queryset"] = Roster.objects.filter(registered=None,auditing=None,con=challenge.con)
        return super(ChallengeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class TrainingResource(resources.ModelResource):
    class Meta:
        model = Training
        fields = ('id','name','location_type','RCaccepted','registered__intl','registered__skill','registered__gender','duration','onsk8s','contact','coach','created_on','description','regcap','audcap','con','con__city','con__year')
        export_order=fields
        #I think I don't want to import this one, only export. too compex. don't think I can specify that, though.
        import_id_fields = ('coach','con')
        skip_unchanged = True
        report_skipped = True


class TrainingAdmin(ImportExportActionModelAdmin):
    list_display= ('name','con')
    search_fields = ('name', 'con__year')
    filter_horizontal = ('coach',)
    list_filter = ('con','onsk8s','registered__skill','registered__intl','registered__gender','location_type','contact')
    resource_class = TrainingResource
    inlines = [
        RegisteredInline, AuditingInline
    ]

    def view_on_site(self, training):
        from scheduler.views import view_training
        return 'localhost:8000' + reverse('scheduler.views.view_training',
                                              kwargs={'activity_id': training.pk})

class CoachResource(resources.ModelResource):
    class Meta:
        model = Coach
        fields = ('id','user','description','can_email','user__email','user__first_name','user__last_name','user__username')
        export_order=fields
        #I think I don't want to import this one, only export. too compex. don't think I can specify that, though.
        import_id_fields = ('user',)
        skip_unchanged = True
        report_skipped = True


class CoachAdmin(ImportExportActionModelAdmin):
    search_fields = ('user__first_name', 'user__last_name')
    resource_class = CoachResource
    view_on_site = True


# class HappeningAdmin(admin.ModelAdmin):
#     #list_display= ('name', 'captain','cap')
#     #search_fields = ('name', 'captain')
#     #exclude=('participants',)
#     list_display = [field.name for field in Happening._meta.fields if field.name != "id"]#shows all but m2m fields

admin.site.register(Venue, VenueAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Roster, RosterAdmin)
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Coach, CoachAdmin)
#admin.site.register(Happening, HappeningAdmin)
