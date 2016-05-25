#scheduler admin
from con_event.models import Con,Registrant, SKILL_LEVEL_TNG,SKILL_LEVEL_CHG,SKILL_LEVEL, SKILL_LEVEL_ACT
from django.contrib import admin
from scheduler.models import Venue, Location, Roster, Challenge, Training, Coach
from import_export import resources,fields
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
    list_display= ('venue','name','abbrv','location_type')
    search_fields = ('venue__name','name','abbrv','location_type')
    list_filter = ('location_type','venue__name')
    list_display_links = list_display


# class RegisteredInline(admin.StackedInline):
#     model = Roster
#     fk_name = "registered"
#     fields=(('intl','gender','skill'),'participants')
#     filter_horizontal = ('participants',)
#
#     def formfield_for_choice_field(self, db_field, request, **kwargs):
#         #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
#         if db_field.name == "skill":
#             kwargs['choices'] =  SKILL_LEVEL_TNG
#         return super(RegisteredInline, self).formfield_for_choice_field(db_field, request, **kwargs)
#
#     def formfield_for_manytomany(self, db_field, request, **kwargs):
#         try:#So will still work when making a new one
#             training_id = resolve(request.path).args[0]
#             training=Training.objects.get(pk=training_id)
#             if db_field.name == "participants":
#                 kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=training.con)
#             return super(RegisteredInline, self).formfield_for_manytomany(db_field, request, **kwargs)
#         except:
#             if db_field.name == "participants":
#                 kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater','Offskates'])
#             return super(RegisteredInline, self).formfield_for_manytomany(db_field, request, **kwargs)
#
# class AuditingInline(admin.StackedInline):
#     model = Roster
#     fk_name = "auditing"
#     fields=(('intl','gender','skill'),'participants')
#     filter_horizontal = ('participants',)
#
#     def formfield_for_choice_field(self, db_field, request, **kwargs):
#         #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
#         if db_field.name == "skill":
#             kwargs['choices'] =  SKILL_LEVEL_TNG
#         return super(AuditingInline, self).formfield_for_choice_field(db_field, request, **kwargs)
#
#     def formfield_for_manytomany(self, db_field, request, **kwargs):
#         try:#So will still work when making a new one
#             training_id = resolve(request.path).args[0]
#             training=Training.objects.get(pk=training_id)
#             if db_field.name == "participants":
#                 kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater','Offskates'],con=training.con)
#             return super(AuditingInline, self).formfield_for_manytomany(db_field, request, **kwargs)
#         except:
#             if db_field.name == "participants":
#                 kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater','Offskates'])
#             return super(AuditingInline, self).formfield_for_manytomany(db_field, request, **kwargs)

class RosterResource(resources.ModelResource):
    class Meta:
        model = Roster
        fields = ('id','name','captain','captain__sk8name','color','skill','gender','intl','internal_notes','con','con__city','con__year')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        export_order=fields
        import_id_fields = ('captain','con')
        skip_unchanged = True
        report_skipped = True

#class RosterAdmin(ImportExportActionModelAdmin):#This puts the export button with the Action thing, where you delete. DANGER easy to almost delete
class RosterAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
    fields = (('con','name','color'),('captain','can_email'),('skill','gender','intl'),'participants','internal_notes')
    list_display= ('name', 'captain','Challenge_Name','con','cap')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('name', 'captain__sk8name', 'captain__first_name','captain__last_name')
    filter_horizontal = ('participants',)
    list_filter = ('con','skill','gender','intl')
    resource_class = RosterResource

    def Challenge_Name(self, obj):
        if obj:
            chals=list(obj.roster1.all())+list(obj.roster2.all())
        names=""
        for c in chals:
            names+=str(c.name)+" "
        return names

    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        try:#So will still work when making a new one
            object_id = resolve(request.path).args[0]
            roster=Roster.objects.get(pk=object_id)
            if db_field.name == "captain":
                kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=roster.con)
        except:
            pass
        return super(RosterAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        try:#So will still work when making a new one
            object_id = resolve(request.path).args[0]
            roster=Roster.objects.get(pk=object_id)
            if db_field.name == "participants":
                kwargs["queryset"] = Registrant.objects.filter(pass_type__in=['MVP', 'Skater'],con=roster.con)
        except:
            pass
        return super(RosterAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        #http://stackoverflow.com/questions/864433/how-to-modify-choices-on-admin-pages-django
        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_ACT#activity bc this could refer to either training or challenge, at this point
        return super(RosterAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)


class ChallengeResource(resources.ModelResource):
    #thanks! http://stackoverflow.com/questions/25849480/django-import-export-export-from-models-functions
    duration_display=fields.Field()
    gametype_display=fields.Field()

    skill_display=fields.Field()
    gender_display=fields.Field()


    def dehydrate_duration_display(self,challenge):
        return challenge.get_duration_display()

    def dehydrate_gametype_display(self,challenge):
        return challenge.get_gametype_display()

    def dehydrate_skill_display(self,challenge):
        return challenge.skill_display()

    def dehydrate_gender_display(self,challenge):
        return challenge.gender_display()

    class Meta:
        model = Challenge
        #fields = ('id','name','roster1','duration_display','gametype_display','roster1__name','roster1__captain','roster1__captain__sk8name','communication','captain1accepted','roster1score','roster2','roster2__name','roster2__captain','roster2__captain__sk8name','captain2accepted','roster2score','is_a_game','location_type','RCaccepted','ruleset','submitted_on','internal_notes','con','con__city','con__year')
        fields = ('id','name','roster1','duration_display','gametype_display','skill_display','gender_display','roster1__captain__sk8name','communication','captain1accepted','roster2','roster2__captain__sk8name','captain2accepted','is_a_game','location_type','RCaccepted','ruleset','submitted_on','con__year')
        #note to self: to include fk fields in export order, you need to specify fields. doesn't work if you do exclude.
        #export_order=fields
        export_order= ('id','name','skill_display','gender_display','is_a_game','duration_display','gametype_display','location_type','RCaccepted','submitted_on','ruleset','communication','captain1accepted','captain2accepted','roster1','roster1__captain__sk8name','roster2','roster2__captain__sk8name','con__year')

        #I think I don't want to import this one, only export. too compex. don't think I can specify that, though.
        import_id_fields = ('roster1','roster1__captain','roster2','roster2__captain','con')
        skip_unchanged = True
        report_skipped = True

class ChallengeAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
#class ChallengeAdmin(ImportExportActionModelAdmin):#This puts the export button with the Action thing, where you delete. DANGER easy to almost delete
    list_display= ('name', 'Captains','con','gametype','location_type','submitted_on','RCaccepted')
    list_display_links = list_display#makes everything in list display clickable to get to object
    search_fields = ('name','roster1__name', 'roster2__name','roster1__captain__sk8name','roster2__captain__sk8name')
    fields = (('con','RCaccepted','RCrejected'),('location_type','ruleset','gametype'),('created_on','submitted_on'),
        ('roster1','captain1accepted','roster1score'),('roster2','captain2accepted','roster2score'),'internal_notes','communication')
    list_filter = ('con','location_type','is_a_game')
    resource_class = ChallengeResource

    def Captains(self, obj):
        cstr=""
        if obj:
            cno=0
            for r in [obj.roster1,obj.roster2]:
                if r and r.captain:
                    cno+=1
                    if cno>1:
                        cstr+=" & "
                    cstr+=r.captain.name
        return cstr

    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        try:#So will still work when making a new one
            challenge_id = resolve(request.path).args[0]
            challenge=Challenge.objects.get(pk=challenge_id)
            if db_field.name in ["roster1","roster2"]:
                #I could maybe filter by cap as well, to ensure only get game teams? worried i'll forget about that and cause problems.
                kwargs["queryset"] = Roster.objects.filter(registered=None,auditing=None,con=challenge.con)
            return super(ChallengeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        except:
            if db_field.name in ["roster1","roster2"]:
                #I could maybe filter by cap as well, to ensure only get game teams? worried i'll forget about that and cause problems.
                kwargs["queryset"] = Roster.objects.filter(registered=None,auditing=None)
            return super(ChallengeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class TrainingResource(resources.ModelResource):

    duration_display=fields.Field()
    coach_name=fields.Field()

    def dehydrate_duration_display(self,training):
        return training.get_duration_display()

    def dehydrate_coach_name(self,training):
        names=""
        for c in training.coach.all():
            names+=c.user.first_name+", "
        if len(names)>2:
            names=names[:-2]

        return names


    class Meta:
        model = Training
        # fields = ('id','name','location_type','RCaccepted','registered__intl','registered__skill','duration','onsk8s','contact','coach','created_on','description','regcap','audcap','internal_notes','con','con__city','con__year')
        # export_order=fields
        fields = ('id','name','location_type','duration_display','RCaccepted','registered__intl','registered__skill','onsk8s','contact','coach_name','created_on','description','regcap','audcap','con__year')
        export_order=fields

        #I think I don't want to import this one, only export. too compex. don't think I can specify that, though.
        import_id_fields = ('coach','con')
        skip_unchanged = True
        report_skipped = True


class TrainingAdmin(ImportExportModelAdmin):#this has its own obvious expost button, but then you need to export all instances
#class TrainingAdmin(ImportExportActionModelAdmin):#This puts the export button with the Action thing, where you delete. DANGER easy to almost delete
    list_display= ('name','con')
    search_fields = ('name', 'con__year')
    filter_horizontal = ('coach',)
    list_filter = ('con','RCaccepted','onsk8s','registered__skill','registered__intl','registered__gender','location_type','contact')
    resource_class = TrainingResource
    fields = (('name','con','location_type'),('RCaccepted','RCrejected'),('skill','onsk8s','contact','regcap','audcap','duration'),'coach','description','internal_notes','communication')
    # inlines = [
    #     RegisteredInline, AuditingInline
    # ]

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

class CoachAdmin(ImportExportModelAdmin):
#class CoachAdmin(ImportExportActionModelAdmin):
    search_fields = ('user__username','user__first_name', 'user__last_name')
    #list_display= ('user',)
    resource_class = CoachResource
    view_on_site = True


admin.site.register(Venue, VenueAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Roster, RosterAdmin)
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Coach, CoachAdmin)
