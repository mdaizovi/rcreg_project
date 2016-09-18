from django import forms
from django.contrib import admin
from django.core.urlresolvers import reverse, resolve
from django.forms import ModelForm

from con_event.models import Con, Registrant, SKILL_LEVEL_CHG

from import_export import resources, fields
from import_export.admin import (ImportExportModelAdmin,
        ImportExportActionModelAdmin
        )
from scheduler.models import (Venue, Location, Roster, Challenge, Training,
        Coach, ReviewTraining, ReviewCon
        )


#===============================================================================
class LocationInline(admin.TabularInline):

    model = Location
    fields = ('name', 'location_type')


#===============================================================================
class VenueAdmin(admin.ModelAdmin):

    list_display= ('name', )
    search_fields = ('name', )
    inlines = [LocationInline]


#===============================================================================
class LocationAdmin(admin.ModelAdmin):

    list_display= ('venue', 'name', 'abbrv', 'location_type')
    search_fields = ('venue__name', 'name','abbrv', 'location_type')
    list_filter = ('location_type', 'venue__name')
    list_display_links = list_display


#===============================================================================
class RosterResource(resources.ModelResource):

    #---------------------------------------------------------------------------
    class Meta:

        model = Roster
        fields = ('id', 'name', 'captain', 'captain__sk8name', 'color', 'skill',
                'gender', 'intl', 'internal_notes', 'con', 'con__city',
                'con__year'
                )
        export_order = fields
        import_id_fields = ('captain', 'con')
        skip_unchanged = True
        report_skipped = True


#===============================================================================
class RosterAdmin(ImportExportModelAdmin):

    fields = (('con', 'name', 'color'), ('captain', 'can_email'),
            ('skill', 'gender', 'intl'), 'participants', 'internal_notes'
            )
    list_display = ('name', 'captain', 'challenge_name', 'con', 'cap')
    list_display_links = list_display
    search_fields = ('name', 'captain__sk8name', 'captain__first_name',
            'captain__last_name',
            )
    filter_horizontal = ('participants',)
    list_filter = ('con', 'skill', 'gender', 'intl')
    resource_class = RosterResource

    #---------------------------------------------------------------------------
    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        """If roster exists, limits captain queryset to registrants with
        Skater or MVP pass of same con as Roster.
        """

        try:  # So will still work when making a new one, no con yet.
            object_id = resolve(request.path).args[0]
            roster = Roster.objects.get(pk=object_id)
            if db_field.name == "captain":
                kwargs["queryset"] = (Registrant.objects.filter(
                        pass_type__in=['MVP', 'Skater'], con=roster.con)
                        )
        except:  # unlimited, huge queryet.
            pass

        return (super(
                RosterAdmin, self).formfield_for_foreignkey(
                        db_field, request, **kwargs
                        )
                )

    #---------------------------------------------------------------------------
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """If roster exists, limits participant queryset to registrants with
        Skater or MVP pass of same con as Roster.
        """

        try:  # So will still work when making a new one, no con yet.
            object_id = resolve(request.path).args[0]
            roster = Roster.objects.get(pk=object_id)
            if db_field.name == "participants":
                kwargs["queryset"] = (Registrant.objects.filter(
                        pass_type__in=['MVP', 'Skater'], con=roster.con)
                        )
        except:  # unlimited, huge queryset.
            pass

        return (super(
                RosterAdmin, self).formfield_for_manytomany(
                        db_field, request, **kwargs
                        )
                )

    #---------------------------------------------------------------------------
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Limits skill choices to those which are appropriate for activity."""

        if db_field.name == "skill":
            kwargs['choices'] =  SKILL_LEVEL_CHG

        return (super(
                RosterAdmin, self).formfield_for_choice_field(
                        db_field, request, **kwargs
                        )
                )


#===============================================================================
class ChallengeResource(resources.ModelResource):

    duration_display = fields.Field()
    gametype_display = fields.Field()
    skill_display = fields.Field()
    gender_display = fields.Field()

    #---------------------------------------------------------------------------
    def dehydrate_duration_display(self,challenge):
        return challenge.get_duration_display()

    #---------------------------------------------------------------------------
    def dehydrate_gametype_display(self,challenge):
        return challenge.get_gametype_display()

    #---------------------------------------------------------------------------
    def dehydrate_skill_display(self,challenge):
        return challenge.skill_display()

    #---------------------------------------------------------------------------
    def dehydrate_gender_display(self,challenge):
        return challenge.gender_display()

    #---------------------------------------------------------------------------
    class Meta:

        model = Challenge
        fields = ('id', 'name', 'roster1', 'duration_display',
                'gametype_display', 'skill_display', 'gender_display',
                'roster1__captain__sk8name', 'communication',
                'captain1accepted', 'roster2', 'roster2__captain__sk8name',
                'captain2accepted', 'location_type', 'RCaccepted',
                'ruleset', 'submitted_on', 'con__year'
                )
        export_order = ('id', 'name', 'skill_display', 'gender_display',
                'duration_display', 'gametype_display',
                'location_type', 'RCaccepted', 'submitted_on', 'ruleset',
                'communication', 'captain1accepted', 'captain2accepted',
                'roster1', 'roster1__captain__sk8name', 'roster2',
                'roster2__captain__sk8name', 'con__year'
                )
        import_id_fields = ('roster1', 'roster1__captain', 'roster2',
                'roster2__captain', 'con'
                )
        skip_unchanged = True
        report_skipped = True


#===============================================================================
class ChallengeAdmin(ImportExportModelAdmin):

    list_display = ('name', 'figurehead_display', 'con', 'gametype',
            'location_type', 'submitted_on', 'RCaccepted'
            )
    list_display_links = list_display
    search_fields = ('name', 'roster1__name', 'roster2__name',
            'roster1__captain__sk8name', 'roster2__captain__sk8name'
            )
    fields = (('con', 'RCaccepted', 'RCrejected','interest'),
            ('location_type', 'ruleset', 'gametype'),
            ('created_on', 'submitted_on'),
            ('roster1', 'captain1accepted', 'roster1score'),
            ('roster2', 'captain2accepted', 'roster2score'),
            'internal_notes', 'communication'
            )
    list_filter = ('con', 'location_type', 'gametype')
    resource_class = ChallengeResource

    #---------------------------------------------------------------------------
    def formfield_for_foreignkey(self, db_field, request,**kwargs):
        """If challenge exists, limits roster queryset to same con."""

        try:  # So will still work when making a new one, no con yet.
            challenge_id = resolve(request.path).args[0]
            challenge = Challenge.objects.get(pk=challenge_id)
            if db_field.name in ["roster1", "roster2"]:
                kwargs["queryset"] = Roster.objects.filter(con=challenge.con)
        except:
            pass

        return (super(ChallengeAdmin, self).formfield_for_foreignkey(
                db_field, request, **kwargs)
                )


#===============================================================================
class TrainingResource(resources.ModelResource):

    duration_display = fields.Field()
    figurehead_display = fields.Field()

    #---------------------------------------------------------------------------
    def dehydrate_duration_display(self,training):
        return training.get_duration_display()
    #---------------------------------------------------------------------------
    def dehydrate_figurehead_display(self,training):
        return training.figurehead_display

    #---------------------------------------------------------------------------
    class Meta:
        model = Training
        fields = ('id', 'name', 'location_type', 'duration_display',
                'RCaccepted', 'skill',
                'onsk8s', 'contact', 'figurehead_display', 'created_on',
                'description', 'regcap', 'audcap', 'con__year'
                )
        export_order = fields
        import_id_fields = ('coach', 'con')
        skip_unchanged = True
        report_skipped = True


#===============================================================================
class TrainingAdmin(ImportExportModelAdmin):

    list_display = ('name', 'con', 'figurehead_display')
    search_fields = ('name', 'con__year')
    filter_horizontal = ('coach', )
    list_filter = ('con', 'RCaccepted', 'onsk8s', 'skill', 'location_type', 'contact')
    resource_class = TrainingResource
    fields = (('name', 'con', 'location_type'),
            ('RCaccepted', 'RCrejected', 'interest', 'sessions'),
            ('skill', 'onsk8s', 'contact', 'regcap', 'audcap', 'duration'),
            'coach', 'description', 'internal_notes', 'communication'
            )

    #---------------------------------------------------------------------------
    def view_on_site(self, training):

        from scheduler.views import view_training

        site_string = ('http://www.rollertron.com'
                + reverse('scheduler.views.view_training',
                        kwargs={'activity_id': training.pk}
                        )
                )
        return site_string


#===============================================================================
class CoachResource(resources.ModelResource):

    class Meta:
        model = Coach
        fields = ('id', 'user', 'description', 'can_email', 'user__email',
                'user__first_name', 'user__last_name', 'user__username'
                )
        export_order = fields
        import_id_fields = ('user', )
        skip_unchanged = True
        report_skipped = True


#===============================================================================
class CoachAdmin(ImportExportModelAdmin):

    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    resource_class = CoachResource
    view_on_site = True


# #===============================================================================
# class ReviewTrainingResource(resources.ModelResource):
#
#     #---------------------------------------------------------------------------
#     class Meta:
#         model = ReviewTraining
#         fields = ('date', 'training', 'prepared', 'articulate', 'hear',
#                 'learn_new', 'recommend', 'another_class',
#                 'skill_level_expected', 'drills_helpful', 'share_feedback',
#                 'league_visit', 'league_referral', 'comments_text',
#                 'registrant__age_group', 'registrant__skill',
#                 'registrant__gender', 'registrant__country'
#                 )
#         export_order = fields
#         skip_unchanged = True
#         report_skipped = True
#
#
# #===============================================================================
# class ReviewTrainingAdmin(ImportExportModelAdmin):
#
#     search_fields = ('training__name', )
#     list_display = ('training', )
#     list_filter = ('training__con', 'training__onsk8s')
#     resource_class = ReviewTrainingResource
#     fields = (('training'), ('prepared', 'articulate', 'hear', 'learn_new',
#                             'recommend', 'another_class'),
#         ('skill_level_expected', 'drills_helpful'),
#         ('share_feedback', 'league_visit', 'league_referral', 'comments_text')
#         )
#
#
# #===============================================================================
# class ReviewConResource(resources.ModelResource):
#
#     #---------------------------------------------------------------------------
#     class Meta:
#         model = ReviewCon
#         fields = ('overall_exp','onsk8s','offsk8s','seminars','competitive_events_playing','competitive_events_watching','social_events','shopping','lines',
#             'fav1','fav2','rank_training','rank_competition_playing','rank_competition_watching','rank_seminars','rank_social','rank_shopping','rank_volunteer',
#             'comments_text','ruleset','years_playing','RC_Experience')
#         export_order=fields
#         skip_unchanged = True
#         report_skipped = True
#
#
# #===============================================================================
# class ReviewConAdmin(ImportExportModelAdmin):
#     search_fields = ('registrant__con',)
#     list_filter = ('registrant__con',)
#     resource_class = ReviewConResource
#     fields = (('overall_exp'),
#         ('onsk8s','offsk8s','seminars','competitive_events_playing','competitive_events_watching','social_events','shopping','lines'),
#         ('fav1','fav2'),('rank_training','rank_competition_playing','rank_competition_watching','rank_seminars','rank_social','rank_shopping','rank_volunteer'),
#         ('comments_text',),('ruleset','years_playing','RC_Experience'))

#===============================================================================
admin.site.register(Venue, VenueAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Roster, RosterAdmin)
admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Coach, CoachAdmin)
#admin.site.register(ReviewTraining, ReviewTrainingAdmin)
#admin.site.register(ReviewCon, ReviewConAdmin)
