from django import forms
from django.db.models import Q
from django.forms import ModelForm, modelformset_factory
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from con_event.models import (LOCATION_TYPE, GENDER, Con, Registrant,
        SKILL_LEVEL_TNG, SKILL_LEVEL_CHG, SKILL_LEVEL_ACT
        )
from rcreg_project.extras import remove_punct, ascii_only, ascii_only_no_punct
from scheduler.app_settings import (DEFAULT_ONSK8S_DURATION,
        DEFAULT_OFFSK8S_DURATION, DEFAULT_CHALLENGE_DURATION,
        DEFAULT_SANCTIONED_DURATION
        )
from scheduler.models import (Coach, SESSIONS_TR, COLORS, GAMETYPE, RULESET,
        Challenge, Training, Roster, DURATION
        )

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

        choices = SKILL_LEVEL_CHG

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
        self.fields["con"].initial = conlist[0]

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

        MY_TEAMS = []
        # Provide list of rosters input, likely rosters registrant is captaining
        for r in team_list:
            if r.name:
                MY_TEAMS.append((str(r.pk), str(r.name)))
            else:
                MY_TEAMS.append((str(r.pk), "unnamed team"))

        self.fields["game_team"] = forms.CharField(
                label="Select Team",
                widget=forms.Select(choices=MY_TEAMS),
                required=True,
                initial=MY_TEAMS[0][0]
                )

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


#===============================================================================
class GenderSkillForm(forms.Form):

    #---------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        captain = kwargs.pop('captain')
        super(GenderSkillForm, self).__init__(*args, **kwargs)

        # Try to only include skills captain is eligible for
        skill_options = []
        if captain.skill:
            for s in SKILL_LEVEL_CHG[1:]:
                if captain.skill in s[0]:
                    skill_options.append(s)
        else:
            # So won't be problem if captain didn't specify skill
            skill_options = SKILL_LEVEL_CHG

        #  Defining fields
        self.fields["skill"] = (forms.CharField(
                widget=forms.Select(choices=skill_options),
                initial=captain.skill+"O",
                label='Skill Level')
                )
        self.fields["gender"] = (forms.CharField(
                widget=forms.Select(choices=GENDER),
                initial=captain.gender,
                label='Restrict Participant Gender?')
                )

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})


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
            roster2name = "unnamed team"

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


#===============================================================================
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
