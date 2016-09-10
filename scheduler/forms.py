from django import forms
from django.db.models import Q
from django.forms import ModelForm, modelformset_factory
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from con_event.models import (LOCATION_TYPE, GENDER, Con, Registrant,
        SKILL_LEVEL_TNG, SKILL_LEVEL_CHG, SKILL_LEVEL_ACT,SKILL_LEVEL_GAME
        )
from rcreg_project.extras import remove_punct, ascii_only, ascii_only_no_punct
from scheduler.app_settings import (DEFAULT_ONSK8S_DURATION,
        DEFAULT_OFFSK8S_DURATION, DEFAULT_CHALLENGE_DURATION,
        DEFAULT_SANCTIONED_DURATION
        )
from scheduler.models import (GET_NUMBER_RATINGS, RC_REVIEW_DICT,
        GET_RC_EXPERIENCE, Coach, SESSIONS_TR, COLORS, GAMETYPE, RULESET,
        Challenge, Training, Roster, ReviewTraining, ReviewCon, DURATION
        )


SIMPLIFIED_LOCATION_TYPE = LOCATION_TYPE[:2]
BINARY_WORDS = (("No", 'No'), ("Yes", 'Yes'))
BINARY_HALF_WORDS = ((False, 'No'), (True, 'Yes'))


#===============================================================================
class TrainingModelForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        conlist = user.all_cons()
        super(TrainingModelForm, self).__init__(*args, **kwargs)

        #  Defining fields
        self.fields["onsk8s"] = (forms.CharField(
                widget=forms.Select(choices=BINARY_HALF_WORDS),
                initial=BINARY_HALF_WORDS[1][0],
                label='On Skates?')
                )
        self.fields["contact"] = (forms.CharField(
                widget=forms.Select(choices=BINARY_HALF_WORDS),
                initial=BINARY_HALF_WORDS[1][0],
                label='Contact?')
                )
        self.fields["location_type"] = (forms.CharField(
                widget=forms.Select(choices=LOCATION_TYPE),
                initial=LOCATION_TYPE[0][0],
                label='Location Type')
                )
        self.fields["sessions"] = (forms.CharField(widget=forms.Select(
                choices=SESSIONS_TR),
                initial=SESSIONS_TR[0][0],
                label='How Many Sessions Would You Like to Offer?')
                )
        self.fields["communication"] = (forms.CharField(
                widget=forms.Textarea(),
                label='Scheduling Notes Between Coaches & RC Staff \
                        (visible to you and them only)',
                required=False)
                )

        #  Modifying fields
        self.fields["con"].queryset = Con.objects.filter(
                id__in=[o.id for o in conlist]
                )
        self.fields["con"].initial = conlist[0]


        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    })

    #---------------------------------------------------------------------------
    class Meta:
        model = Training
        fields =[
                'name', 'con', 'location_type', 'onsk8s', 'contact', 'skill',
                'sessions', 'description', 'communication'
                ]
        labels = {
                'name': _('Name'),
                'description': _('Description'),
                }


#===============================================================================
class ChallengeRosterModelForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')

        #  Try to make roster skill and gender match user registrant.
        # else default to Female w/ no skill
        try:
            reglist = user.registrants()
            most_u = reglist[0]
            initial_gender = most_u.gender
            initial_skill = most_u.skill+"O"
        except:
            initial_skill = SKILL_LEVEL_CHG[1][0]
            initial_gender = GENDER[0][0]

        super(ChallengeRosterModelForm, self).__init__(*args, **kwargs)

        choices = SKILL_LEVEL_CHG[1:]
        if self.instance:
            clist = (list(
                    self.instance.roster1.all())
                    + list(self.instance.roster2.all()
                    ))
            if len(clist) > 0:
                c = clist[0]
                if c.is_a_game:
                    choices = SKILL_LEVEL_GAME

        #  Defining fields
        self.fields["skill"] = (forms.CharField(
                widget=forms.Select(choices=choices),
                initial=initial_skill,
                label='Skill Level')
                )
        self.fields["color"] = (forms.CharField(
                widget=forms.Select(choices=COLORS),
                initial=COLORS[0][0],
                label='Team Color')
                )
        self.fields["can_email"] = (forms.CharField(
                widget=forms.Select(choices=BINARY_HALF_WORDS),
                initial=BINARY_HALF_WORDS[1][0],
                label='Can skaters rostered on this team use this site \
                        to send you emails?')
                )
        #  Modifying fields
        self.fields["gender"].initial = initial_gender
        self.fields["name"].initial = ""

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    })

    #---------------------------------------------------------------------------
    class Meta:

        model = Roster
        fields = ['name','color','skill','gender','can_email']
        labels = {
                'name': _('Team Name'),
                'gender': _('Restrict Participant Gender?'),
                }


#===============================================================================
class ChallengeModelForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        reglist = user.registrants()
        super(ChallengeModelForm, self).__init__(*args, **kwargs)

        conlist=[]
        for reg in reglist:
            #  If has MVP or sk8er pass. Just registrant not good enough.
            if  reg.can_sk8():
                conlist.append(reg.con)

        #  Defining fields
        self.fields["location_type"] = forms.CharField(
                widget=forms.Select(choices=LOCATION_TYPE[:3]),
                initial=LOCATION_TYPE[0][0],
                label='Location Type'
                )
        self.fields["ruleset"] = forms.CharField(
                widget=forms.Select(choices=RULESET),
                initial=RULESET[0][0],
                label='Rules'
                )
        self.fields["gametype"] = forms.CharField(
                widget=forms.Select(choices=GAMETYPE),
                initial=GAMETYPE[0][0],
                label='Type'
                )
        self.fields["communication"] = forms.CharField(
                widget=forms.Textarea(),
                label='Notes Between Captains & Officials (visible to skaters \
                        on both teams; can be left blank)',
                required=False
                )

        #  Modifying fields
        self.fields["con"].queryset = Con.objects.filter(
                id__in=[o.id for o in conlist]
                )
        self.fields["con"].initial = conlist[-1]

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    })

    #---------------------------------------------------------------------------
    class Meta:

        model = Challenge
        fields = ['con', 'location_type', 'ruleset', 'gametype', 'communication']


#===============================================================================
class MyRosterSelectForm(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        team_list = kwargs.pop('team_list')
        super(MyRosterSelectForm, self).__init__(*args, **kwargs)

        MY_TEAMS=[]
        # Provide list of rosters input, likely rosters registrant is captaining
        for r in team_list:
            if r.name:
                MY_TEAMS.append((str(r.pk), str(r.name)))
            else:
                MY_TEAMS.append((str(r.pk), "unnamed team"))

        self.fields["game_team"]=forms.CharField(
                label="Select Team",
                widget=forms.Select(choices=MY_TEAMS),
                required=True,
                initial=MY_TEAMS[0][0]
                )

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


#===============================================================================
class GameRosterCreateModelForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(GameRosterCreateModelForm, self).__init__(*args, **kwargs)
        self.fields["name"].initial = ""

        #  Defining fields
        self.fields["color"] = forms.CharField(
                widget=forms.Select(choices=COLORS),
                initial=COLORS[0][0],
                label='Team Color'
                )
        self.fields["can_email"] = forms.CharField(
                widget=forms.Select(choices=BINARY_HALF_WORDS),
                initial=BINARY_HALF_WORDS[1][0],
                label='Can skaters rostered on this team use this site to \
                        send you emails?'
                )
        #  Modifying fields
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    })

    #---------------------------------------------------------------------------
    class Meta:
        model = Roster
        fields = ['name','color','can_email']
        labels = {
                'name': _('Team Name'),
                }


#===============================================================================
class GameModelForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(GameModelForm, self).__init__(*args, **kwargs)
        reglist = user.registrants()
        conlist=[]
        for reg in reglist:
            #  If has MVP or sk8er pass. Just registrant not good enough.
            if  reg.can_sk8():
                conlist.append(reg.con)

        #  Defining fields
        self.fields["location_type"] = forms.CharField(
                widget=forms.Select(choices=LOCATION_TYPE[:3]),
                initial=LOCATION_TYPE[0][0],
                label='Location Type'
                )
        self.fields["ruleset"] = forms.CharField(
                widget=forms.Select(choices=RULESET),
                initial=RULESET[0][0],
                label='Rules'
                )
        self.fields["communication"] = forms.CharField(
                widget=forms.Textarea(),
                label='Notes Between Captains & Officials (visible to skaters \
                        on both teams; can be left blank)',
                required=False
                )

        #  Modifying fields
        self.fields["con"].queryset = Con.objects.filter(
                id__in=[o.id for o in conlist]
                )
        self.fields["con"].initial = conlist[-1]

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    })

    #---------------------------------------------------------------------------
    class Meta:

        model = Challenge
        fields = ['con', 'location_type', 'ruleset', 'communication']



#===============================================================================
class ScoreFormDouble(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        challenge = kwargs.pop('my_arg')
        super(ScoreFormDouble, self).__init__(*args, **kwargs)

        # I don't know why the rosters would make it this far without a name.
        # Just in case.
        if challenge.roster1:
            roster1name = challenge.roster1.name
        else:
            roster1name = "unnamed team"

        if challenge.roster2:
            roster2name = challenge.roster2.name
        else:
            roster2name="unnamed team"

        self.fields["roster1_score"] = forms.IntegerField(
                initial=challenge.roster1score,
                label=('%s Score' % (roster1name)),
                min_value=0
                )
        self.fields["roster2_score"] = forms.IntegerField(
                initial=challenge.roster2score,
                label=('%s Score' % (roster2name)),
                min_value=0
                )
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CommunicationForm(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        super(CommunicationForm, self).__init__(*args, **kwargs)
        self.fields["communication"] = forms.CharField(
                widget=forms.Textarea,
                required=False
                )
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


#===============================================================================
class DurationOnly(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(DurationOnly, self).__init__(*args, **kwargs)
        self.fields["duration"] = forms.CharField(
                label="How long will this Training be?",
                widget=forms.Select(choices=DURATION),
                required=True,
                initial=DEFAULT_OFFSK8S_DURATION
                )
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


#===============================================================================
class SendEmail(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(SendEmail, self).__init__(*args, **kwargs)
        self.fields["message"] = forms.CharField(
                widget=forms.Textarea,
                required=True
                )
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


#===============================================================================
class CoachProfileForm(ModelForm):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(CoachProfileForm, self).__init__(*args, **kwargs)
        instancepk = self.instance.id
        self.fields["can_email"] = forms.CharField(
                widget=forms.Select(choices=BINARY_HALF_WORDS),
                initial=BINARY_HALF_WORDS[1][0],
                label='Can this site forward you email messages from other \
                        site users?'
                )
        self.fields["description"] = forms.CharField(
                widget=forms.Textarea(),
                label='Your Coach description',
                required=False
                )

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    #---------------------------------------------------------------------------
    class Meta:

        model = Coach
        fields = ['can_email', 'description']


#===============================================================================
class ChalStatusForm(ModelForm):

    #---------------------------------------------------------------------------
    class Meta:
        model = Challenge
        fields = ['RCaccepted','RCrejected']
        labels = {
                'RCaccepted': _('Accepted'),
                'RCrejected': _('Rejected'),
                }

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        super(ChalStatusForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'id': '%s_for_%s'%(str(field), str(self.instance.pk)),
                    })


#===============================================================================
class TrainStatusForm(ModelForm):

    #---------------------------------------------------------------------------
    class Meta:

        model = Training
        fields = ['RCaccepted', 'RCrejected']
        labels = {
                'RCaccepted': _('Accepted'),
                'RCrejected': _('Rejected'),
                }


    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):

        super(TrainStatusForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'id': '%s_for_%s'%(str(field), str(self.instance.pk)),
                    })


#===============================================================================
class CInterestForm(ModelForm):
    """This is named interest, but for convenience has other fields.
    Helps with scheduling challenges.
    """

    #---------------------------------------------------------------------------
    class Meta:
        model = Challenge
        fields = ['gametype', 'location_type', 'interest']
        labels = {'interest': _('Interest Level'),}

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(CInterestForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'id': '%s_for_%s' % (str(field), str(self.instance.pk)),
                    })


#===============================================================================
class TInterestForm(ModelForm):
    """This is named interest, but for convenience has other fields.
    Helps with scheduling trainings.
    """

    #---------------------------------------------------------------------------
    class Meta:
        model = Training
        fields = ['interest', 'location_type', 'duration', 'sessions']
        labels = {'interest': _('Interest Level')}

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(TInterestForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'id': '%s_for_%s' % (str(field), str(self.instance.pk)),
                    })


#===============================================================================
class ActCheck(forms.Form):
    """Check form used in scheduling to select which activity will be
    approved, rejected, auto-scheduled, etc.
    """

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(ActCheck, self).__init__(*args, **kwargs)
        self.fields["act"] = forms.BooleanField(
                widget=forms.CheckboxInput(),
                initial=True,
                required=False
                )

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                    'style': 'height: 15px; width: 15px; \
                            text-align:center;margin: 0 auto;',
                    'class': 'form-control'
                    })


# #===============================================================================
# class ReviewTrainingForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ReviewTrainingForm, self).__init__(*args, **kwargs)
#
#         self.fields["prepared"].label ="Was the instructor prepared?"
#         self.fields["articulate"].label ="Was the instructor articulate / did you understand the directions?"
#         self.fields["hear"].label ="Could you hear the instructor?"
#         self.fields["learn_new"].label ="Did you learn new things?"
#         self.fields["recommend"].label ="Would you take this class again or recommend it to a teammate?"
#         self.fields["another_class"].label ="Would you take another class with this instructor?"
#         self.fields["skill_level_expected"].label ="Was the skill level what you expected?"
#         self.fields["drills_helpful"].label ="Did you find the drills helpful?"
#         self.fields["share_feedback"].label ="Can we share your feedback with the coach(es)?"
#
#         for field in iter(self.fields):
#             self.fields[field].required = True
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#                 })
#
#     class Meta:
#          model = ReviewTraining
#          exclude = ('date','training','registrant','league_visit','league_referral','comments_text')
#
#
# #===============================================================================
# class ReviewTrainingFormOptional(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ReviewTrainingFormOptional, self).__init__(*args, **kwargs)
#
#         self.fields["league_visit"].label ="Are you interested in having this coach visit your league?"
#         self.fields["league_referral"].label ="If so, please provide league name and email address"
#         self.fields["comments_text"].label ="Do you have any other comments to add?"
#
#         for key in self.fields:
#             self.fields[key].required = False
#
#         for field in iter(self.fields):
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#                 })
#
#     class Meta:
#          model = ReviewTraining
#          fields = ('league_visit','league_referral','comments_text')
#
#
# #===============================================================================
# class ReviewConForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ReviewConForm, self).__init__(*args, **kwargs)
#
#         self.fields['overall_exp'].label ="Your overall experience at RollerCon?"
#         self.fields['onsk8s'].label ="ON SKATES athletic sessions?"
#         self.fields['offsk8s'].label ="OFF SKATES athletic sessions?"
#         self.fields['seminars'].label ="Seminars?"
#         self.fields['competitive_events_playing'].label ="Competitive events you PLAYED IN?"
#         self.fields['competitive_events_watching'].label ="Competitive events you WATCHED?"
#         self.fields['social_events'].label ="Social Events, including the pool, Pants-Off Dance-Off, Black & Blue Ball, etc?"
#         self.fields['shopping'].label ="Shopping opportunities"
#         self.fields['lines'].label="Experience waiting in lines?"
#         self.fields['registrationsys'].label="Registration system?"
#
#         self.fields["fav1"].label ="What was your favorite thing at RollerCon?"
#         self.fields["fav2"].label ="What was your second favorite thing at RollerCon?"
#
#         for key in self.fields:
#             self.fields[key].required = True
#
#         for field in iter(self.fields):
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#                 })
#
#     class Meta:
#          model = ReviewCon
#          exclude = ('date','registrant','ruleset','years_playing','RC_Experience','comments_text','rank_competition_playing','rank_competition_watching','rank_training','rank_seminars','rank_social','rank_shopping','rank_volunteer')
#
#
# #===============================================================================
# class ReviewConRankForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ReviewConRankForm, self).__init__(*args, **kwargs)
#
#         # self.fields['rank_competition_playing']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="PLAYING in Competitive Games (e.g. scrimmages, challenges and full length bouts)")
#         # self.fields['rank_competition_watching']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="WATCHING Competitive Games (e.g. scrimmages, challenges and full length bouts)")
#         # self.fields['rank_training']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Training")
#         # self.fields['rank_seminars']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Seminars")
#         # self.fields['rank_social']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Social Events")
#         # self.fields['rank_shopping']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Shopping/Vendor Village")
#         # self.fields['rank_volunteer']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Opportunities to Volunteer")
#
#         self.fields['rank_competition_playing'].label ="PLAYING in Competitive Games (e.g. scrimmages, challenges and full length bouts)"
#         self.fields['rank_competition_watching'].label ="WATCHING Competitive Games (e.g. scrimmages, challenges and full length bouts)"
#         self.fields['rank_training'].label ="Training"
#         self.fields['rank_seminars'].label ="Seminars"
#         self.fields['rank_social'].label ="Social Events"
#         self.fields['rank_shopping'].label ="Shopping/Vendor Village"
#         self.fields['rank_volunteer'].label ="Opportunities to Volunteer"
#
#
#         for key in self.fields:
#             self.fields[key].required = True
#
#         for field in iter(self.fields):
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#                 })
#
#     class Meta:
#          model = ReviewCon
#          fields = ('rank_competition_playing','rank_competition_watching','rank_training','rank_seminars','rank_social','rank_shopping','rank_volunteer')
#
#
# #===============================================================================
# class ReviewConFormOptional(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ReviewConFormOptional, self).__init__(*args, **kwargs)
#         RC_EXPERIENCE=GET_RC_EXPERIENCE()
#         initial_exp=[]
#         if self.instance and self.instance.RC_Experience:
#             exp_list=self.instance.RC_Experience.split(", ") #stupid unnecessary u'
#             exp_dict=dict(RC_EXPERIENCE)
#             for k in exp_list:
#                 if k in exp_dict:
#                     initial_exp.append(str(k))
#         self.fields["ruleset"].label ="What is ruleset you mostly play under?"
#         self.fields["years_playing"].label ="How many years have you been playing roller derby?"
#         self.fields["RC_Experience"]=forms.CharField(widget=forms.CheckboxSelectMultiple(choices=RC_EXPERIENCE),label ="Please check the box(es) of the year(s) you've participated in RollerCon.")
#         self.fields["comments_text"].label ="Do you have any other comments to add?"
#         self.initial['RC_Experience'] = initial_exp #omg finally fucking works stupid fucking selectmultiple
#
#         for key in self.fields:
#             self.fields[key].required = False
#
#         for field in iter(self.fields):
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#                 })
#
#     class Meta:
#          model = ReviewCon
#          fields = ('ruleset','years_playing','RC_Experience','comments_text')
#
#     def clean_RC_Experience(self):
#         exp_clean = str(self.cleaned_data['RC_Experience'])
#         exp_value1=exp_clean.strip("u'")
#         exp_value2=exp_value1[1:-1]
#         return exp_value2
