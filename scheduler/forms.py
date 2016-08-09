#scheduler.forms
from django import forms
from django.forms import ModelForm,modelformset_factory
from scheduler.models import GET_NUMBER_RATINGS,RC_REVIEW_DICT,GET_RC_EXPERIENCE,Coach,SESSIONS_TR,COLORS,GAMETYPE,RULESET,DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION,DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION,DURATION,Challenge, Training, Roster,ReviewTraining,ReviewCon
from con_event.models import LOCATION_TYPE, GENDER, Con,Registrant,SKILL_LEVEL_TNG,SKILL_LEVEL_CHG,SKILL_LEVEL_ACT,SKILL_LEVEL_GAME
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from django.db.models import Q

SIMPLIFIED_LOCATION_TYPE=LOCATION_TYPE[:2]
BINARY_WORDS=(("No", 'No'),("Yes", 'Yes'))
BINARY_HALF_WORDS=((False, 'No'),(True, 'Yes'))

#I think I don't need this anymore, want to wait before deleting
def UPCOMING_CONS():
    con_list=[]
    for con in Con.objects.upcoming_cons():
        con_tuple=((con.pk),(con),)
        con_list.append(con_tuple)
    return con_list

def unstring_BINARY_WORDS(bin_string):
    print "bin_string is",bin_string
    if bin_string==BINARY_WORDS[0][0]:
        print "unstring_BINARY_WORDS false"
        return False
    else:
        print "unstring_BINARY_WORDS true"
        return True

def USER_UPCOMING_CONS(user):
    '''necessary for submitting trainings and challenges, in case user has more than 1 upcoming con
    after you know putting it here works for training, remove it from the inside of challenge'''
    reg_list=user.upcoming_registrants()
    con_list=[]
    if reg_list:
        for reg in reg_list:
            con_tuple=((reg.con.pk),(reg.con),)
            con_list.append(con_tuple)
            #http://stackoverflow.com/questions/3940128/how-can-i-reverse-a-list-in-python
        return con_list[::-1]#reverse the order in case registered for more than 1, to make most upcoming the default.
    else:
        return None


class TrainingModelForm(ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(TrainingModelForm, self).__init__(*args, **kwargs)
        #conlist=user.upcoming_cons()#this broke for coaches editing old trainings, if didn't have pass for this year
        conlist=user.all_cons()
        try:#have to do it this way so making a new object doesn't break it, but will still populate if editing a past event
            if self.instance.con not in conlist:#found this bug when logged in as admin w/out many cons. or maybe because was no longer upcoming.
                conlist.append(self.instance.con)
        except:
            pass
        #the stuff up here takes precedence over stuff in meta, apparently
        self.fields["con"].queryset =Con.objects.filter(id__in=[o.id for o in conlist])
        self.fields["onsk8s"]=forms.CharField(widget=forms.Select(choices=BINARY_HALF_WORDS),initial=BINARY_HALF_WORDS[1][0], label='On Skates?')
        self.fields["contact"]=forms.CharField(widget=forms.Select(choices=BINARY_HALF_WORDS),initial=BINARY_HALF_WORDS[1][0], label='Contact?')
        self.fields["location_type"]=forms.CharField(widget=forms.Select(choices=LOCATION_TYPE), initial=LOCATION_TYPE[0][0], label='Location Type')
        self.fields["sessions"]=forms.CharField(widget=forms.Select(choices=SESSIONS_TR), initial=SESSIONS_TR[0][0], label='How Many Sessions Would You Like to Offer?')
        self.fields["communication"]=forms.CharField(widget=forms.Textarea(),label='Scheduling Notes Between Coaches & RC Staff (visible to you and them only)',required=False)
        self.fields["con"].initial=conlist[0]

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Training
        fields =['name','con','location_type','onsk8s','contact','skill','sessions','description','communication']
        labels = {
            'name': _('Name'),
            'description': _('Description'),
        }

class ChallengeRosterModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        try:
            upcoming_registrants=user.upcoming_registrants()
            most_u=upcoming_registrants[0]
            initial_gender=most_u.gender
            initial_skill=most_u.skill+"O"
        except:
            initial_skill=SKILL_LEVEL_CHG[1][0]
            initial_gender=GENDER[0][0]

        super(ChallengeRosterModelForm, self).__init__(*args, **kwargs)

        choices=SKILL_LEVEL_CHG[1:]
        if self.instance:
            clist= list(self.instance.roster1.all())+list(self.instance.roster2.all())
            if len(clist)>0:
                c=clist[0]
                if c.is_a_game:
                    choices=SKILL_LEVEL_GAME

        #the stuff up here takes precedence over stuff in meta, apparently
        #self.fields["skill"]=forms.CharField(widget=forms.Select(choices=SKILL_LEVEL_CHG),initial=initial_skill, label='Skill Level')
        self.fields["skill"]=forms.CharField(widget=forms.Select(choices=choices),initial=initial_skill, label='Skill Level')

        self.fields["gender"].initial=initial_gender
        self.fields["name"].initial=""
        self.fields["color"]=forms.CharField(widget=forms.Select(choices=COLORS),initial=COLORS[0][0], label='Team Color')
        self.fields["can_email"]=forms.CharField(widget=forms.Select(choices=BINARY_HALF_WORDS),initial=BINARY_HALF_WORDS[1][0], label='Can skaters rostered on this team use this site to send you emails?')

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Roster
        fields = ['name','color','skill','gender','can_email']
        labels = {
            'name': _('Team Name'),
            'gender': _('Restrict Participant Gender?'),
        }

class ChallengeModelForm(ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(ChallengeModelForm, self).__init__(*args, **kwargs)
        reglist=user.upcoming_registrants()
        conlist=[]
        for reg in reglist:
            if  reg.can_sk8():
                conlist.append(reg.con)
        try:#have to do it this way so making a new object doesn't break it, but will still populate if editing a past event
            if self.instance.con not in conlist:#found this bug when logged in as admin w/out many cons. or maybe because was no longer upcoming.
                conlist.append(self.instance.con)
        except:
            pass
        #the stuff up here takes precedence over stuff in meta, apparently
        self.fields["con"].queryset =Con.objects.filter(id__in=[o.id for o in conlist])
        self.fields["con"].initial=conlist[-1]
        self.fields["location_type"]=forms.CharField(widget=forms.Select(choices=LOCATION_TYPE[:3]), initial=LOCATION_TYPE[0][0], label='Location Type')
        self.fields["ruleset"]=forms.CharField(widget=forms.Select(choices=RULESET), initial=RULESET[0][0], label='Rules')
        self.fields["gametype"]=forms.CharField(widget=forms.Select(choices=GAMETYPE), initial=GAMETYPE[0][0], label='Type')
        self.fields["communication"]=forms.CharField(widget=forms.Textarea(),label='Notes Between Captains & Officials (visible to skaters on both teams; can be left blank)',required=False)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Challenge
        fields = ['con','location_type','ruleset','gametype','communication']

class MyRosterSelectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        team_list = kwargs.pop('team_list')
        super(MyRosterSelectForm, self).__init__(*args, **kwargs)
        MY_TEAMS=[]
        for r in team_list:
            if r.name:
                MY_TEAMS.append((str(r.pk), str(r.name)))
            else:
                MY_TEAMS.append((str(r.pk), "unnamed team"))

        self.fields["game_team"]=forms.CharField(label="Select Team", widget=forms.Select(choices=MY_TEAMS),required=True, initial=MY_TEAMS[0][0])

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class GameRosterCreateModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(GameRosterCreateModelForm, self).__init__(*args, **kwargs)
        self.fields["name"].initial=""
        self.fields["color"]=forms.CharField(widget=forms.Select(choices=COLORS),initial=COLORS[0][0], label='Team Color')
        self.fields["can_email"]=forms.CharField(widget=forms.Select(choices=BINARY_HALF_WORDS),initial=BINARY_HALF_WORDS[1][0], label='Can skaters rostered on this team use this site to send you emails?')

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Roster
        fields = ['name','color','can_email']
        labels = {
            'name': _('Team Name'),
        }

class GameModelForm(ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(GameModelForm, self).__init__(*args, **kwargs)
        reglist=user.upcoming_registrants()
        conlist=[]
        for reg in reglist:
            if  reg.can_sk8():
                conlist.append(reg.con)
        try:#have to do it this way so making a new object doesn't break it, but will still populate if editing a past event
            if self.instance.con not in conlist:#found this bug when logged in as admin w/out many cons. or maybe because was no longer upcoming.
                conlist.append(self.instance.con)
        except:
            pass
        #the stuff up here takes precedence over stuff in meta, apparently
        self.fields["con"].queryset =Con.objects.filter(id__in=[o.id for o in conlist])
        self.fields["con"].initial=conlist[-1]
        self.fields["location_type"]=forms.CharField(widget=forms.Select(choices=LOCATION_TYPE[:3]), initial=LOCATION_TYPE[0][0], label='Location Type')
        self.fields["ruleset"]=forms.CharField(widget=forms.Select(choices=RULESET), initial=RULESET[0][0], label='Rules')
        self.fields["communication"]=forms.CharField(widget=forms.Textarea(),label='Notes Between Captains & Officials (visible to skaters on both teams; can be left blank)',required=False)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Challenge
        fields = ['con','location_type','ruleset','communication']


class ScoreFormDouble(forms.Form):
    def __init__(self, *args, **kwargs):
        challenge = kwargs.pop('my_arg')
        super(ScoreFormDouble, self).__init__(*args, **kwargs)
        if challenge.roster1 and challenge.roster1.name:
            roster1name=challenge.roster1.name
        else:
            roster1name="unnamed team"

        if challenge.roster2 and challenge.roster2.name:
            roster2name=challenge.roster2.name
        else:
            roster2name="unnamed team"

        self.fields["roster1_score"]=forms.IntegerField(label=('%s Score'%(roster1name)), min_value=0,required=False)
        self.fields["roster2_score"]=forms.IntegerField(label=('%s Score'%(roster2name)), min_value=0,required=False)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CommunicationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CommunicationForm, self).__init__(*args, **kwargs)
        self.fields["communication"]=forms.CharField(widget=forms.Textarea,required=False)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class DurationOnly(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DurationOnly, self).__init__(*args, **kwargs)
        self.fields["duration"]=forms.CharField(label="How long will this Training be?", widget=forms.Select(choices=DURATION),required=True, initial=DEFAULT_OFFSK8S_DURATION)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class SendEmail(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SendEmail, self).__init__(*args, **kwargs)
        self.fields["message"]=forms.CharField(widget=forms.Textarea,required=True)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CoachProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(CoachProfileForm, self).__init__(*args, **kwargs)
        instancepk=self.instance.id
        #so beautiful! http://django-datetime-widget.asaglimbeni.me/model_form_v3/
        #self.fields["availability_start"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_start"}, usel10n = True, bootstrap_version=3),label ="OPTIONAL")
        # self.fields["availability_start"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_start"}, usel10n = True, bootstrap_version=3),required=False,label="Availability Start*")
        # self.fields["availability_end"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_end"}, usel10n = True, bootstrap_version=3),required=False,label="Availability End*")
        self.fields["can_email"]=forms.CharField(widget=forms.Select(choices=BINARY_HALF_WORDS),initial=BINARY_HALF_WORDS[1][0], label='Can this site forward you email messages from other site users?')
        self.fields["description"]=forms.CharField(widget=forms.Textarea(),label='Your Coach description',required=False)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
        model = Coach
        fields =['can_email','description']

class ChalStatusForm(ModelForm):
    class Meta:
        model = Challenge
        fields = ['RCaccepted','RCrejected']
        labels = {
            'RCaccepted': _('Accepted'),
            'RCrejected': _('Rejected'),
        }

    def __init__(self, *args, **kwargs):
        super(ChalStatusForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'id': '%s_for_%s'%(str(field),str(self.instance.pk)),
                #'style': "max-lrngth:100px;",
                })

class TrainStatusForm(ModelForm):
    class Meta:
        model = Training
        fields = ['RCaccepted','RCrejected']
        labels = {
            'RCaccepted': _('Accepted'),
            'RCrejected': _('Rejected'),
        }

    def __init__(self, *args, **kwargs):
        super(TrainStatusForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'id': '%s_for_%s'%(str(field),str(self.instance.pk)),
                })

class CInterestForm(ModelForm):
    """This is names interest, but actually has gametype and location type.
    form is meant t help w/ scheduling"""
    class Meta:
        model = Challenge
        fields = ['gametype','location_type','interest']
        labels = {
            'interest': _('Interest Level'),
        }

    def __init__(self, *args, **kwargs):
        super(CInterestForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'id': '%s_for_%s'%(str(field),str(self.instance.pk)),
                })

class TInterestForm(ModelForm):
    """This is names interest, but actually has location type.
    form is meant t help w/ scheduling"""
    class Meta:
        model = Training
        fields = ['interest','location_type','duration','sessions']
        labels = {
            'interest': _('Interest Level'),
        }

    def __init__(self, *args, **kwargs):
        super(TInterestForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'id': '%s_for_%s'%(str(field),str(self.instance.pk)),
                })

class ActCheck(forms.Form):
    def __init__(self, *args, **kwargs):
        # act_type = kwargs.pop('act_type')
        # pk = kwargs.pop('pk')
        super(ActCheck, self).__init__(*args, **kwargs)
        self.fields["act"]=forms.BooleanField(widget=forms.CheckboxInput(),initial=True,required=False)

        for field in iter(self.fields):
            #self.fields[field].widget.attrs.update({'style':'width: 15px','class': 'form-control','name': '%s-%s'%(str(act_type),str(pk))})
            self.fields[field].widget.attrs.update({'style':'height: 15px; width: 15px; text-align:center;margin: 0 auto;','class':'form-control'})




class ReviewTrainingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewTrainingForm, self).__init__(*args, **kwargs)

        self.fields["prepared"].label ="Was the instructor prepared?"
        self.fields["articulate"].label ="Was the instructor articulate / did you understand the directions?"
        self.fields["hear"].label ="Could you hear the instructor?"
        self.fields["learn_new"].label ="Did you learn new things?"
        self.fields["recommend"].label ="Would you take this class again or recommend it to a teammate?"
        self.fields["another_class"].label ="Would you take another class with this instructor?"
        self.fields["skill_level_expected"].label ="Was the skill level what you expected?"
        self.fields["drills_helpful"].label ="Did you find the drills helpful?"
        self.fields["share_feedback"].label ="Can we share your feedback with the coach(es)?"

        for field in iter(self.fields):
            self.fields[field].required = True
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
         model = ReviewTraining
         exclude = ('date','training','registrant','league_visit','league_referral','comments_text')

class ReviewTrainingFormOptional(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewTrainingFormOptional, self).__init__(*args, **kwargs)

        self.fields["league_visit"].label ="Are you interested in having this coach visit your league?"
        self.fields["league_referral"].label ="If so, please provide league name and email address"
        self.fields["comments_text"].label ="Do you have any other comments to add?"

        for key in self.fields:
            self.fields[key].required = False

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
         model = ReviewTraining
         fields = ('league_visit','league_referral','comments_text')

class ReviewConForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewConForm, self).__init__(*args, **kwargs)

        self.fields['overall_exp'].label ="your overall experience at RollerCon?"
        self.fields['onsk8s'].label ="ON SKATES athletic sessions?"
        self.fields['offsk8s'].label ="OFF SKATES athletic sessions?"
        self.fields['seminars'].label ="Seminars?"
        self.fields['competitive_events_playing'].label ="Competitive events you PLAYED IN?"
        self.fields['competitive_events_watching'].label ="Competitive events you WATCHED?"
        self.fields['social_events'].label ="Social Events, including the pool, Pants-Off Dance-Off, Black & Blue Ball, etc?"
        self.fields['shopping'].label ="Shopping opportunities"
        self.fields['lines'].label="Experience waiting in lines?"
        self.fields['registrationsys'].label="Registration system?"

        self.fields["fav1"].label ="What was your favorite thing at RollerCon?"
        self.fields["fav2"].label ="What was your second favorite thing at RollerCon?"

        for key in self.fields:
            self.fields[key].required = True

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
         model = ReviewCon
         exclude = ('date','registrant','ruleset','years_playing','RC_Experience','comments_text','rank_competition_playing','rank_competition_watching','rank_training','rank_seminars','rank_social','rank_shopping','rank_volunteer')

class ReviewConRankForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewConRankForm, self).__init__(*args, **kwargs)

        # self.fields['rank_competition_playing']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="PLAYING in Competitive Games (e.g. scrimmages, challenges and full length bouts)")
        # self.fields['rank_competition_watching']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="WATCHING Competitive Games (e.g. scrimmages, challenges and full length bouts)")
        # self.fields['rank_training']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Training")
        # self.fields['rank_seminars']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Seminars")
        # self.fields['rank_social']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Social Events")
        # self.fields['rank_shopping']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Shopping/Vendor Village")
        # self.fields['rank_volunteer']=forms.ChoiceField(widget=forms.RadioSelect, choices=GET_NUMBER_RATINGS(8,None),label ="Opportunities to Volunteer")

        self.fields['rank_competition_playing'].label ="PLAYING in Competitive Games (e.g. scrimmages, challenges and full length bouts)"
        self.fields['rank_competition_watching'].label ="WATCHING Competitive Games (e.g. scrimmages, challenges and full length bouts)"
        self.fields['rank_training'].label ="Training"
        self.fields['rank_seminars'].label ="Seminars"
        self.fields['rank_social'].label ="Social Events"
        self.fields['rank_shopping'].label ="Shopping/Vendor Village"
        self.fields['rank_volunteer'].label ="Opportunities to Volunteer"


        for key in self.fields:
            self.fields[key].required = True

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
         model = ReviewCon
         fields = ('rank_competition_playing','rank_competition_watching','rank_training','rank_seminars','rank_social','rank_shopping','rank_volunteer')


class ReviewConFormOptional(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewConFormOptional, self).__init__(*args, **kwargs)

        self.fields["ruleset"].label ="What is ruleset you mostly play under?"
        self.fields["years_playing"].label ="How many years have you been playing roller derby?"
        self.fields["RC_Experience"]=forms.CharField(widget=forms.CheckboxSelectMultiple(choices=GET_RC_EXPERIENCE()),label ="Please check the box(es) of the year(s) you've participated in RollerCon.")
        self.fields["comments_text"].label ="Do you have any other comments to add?"

        for key in self.fields:
            self.fields[key].required = False

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    class Meta:
         model = ReviewCon
         fields = ('ruleset','years_playing','RC_Experience','comments_text')

    # def clean(self,):
    #     print "running optional form clean"
    #     if self.is_valid():
    #         experience  = self.cleaned_data["RC_Experience"]
    #
    #         print "experience",experience
    #
    #         new_exp=""
    #         for i in experience:
    #             new_exp+=i+","
    #         print "pre trim ",new_exp
    #         if len(new_exp)>1:
    #             new_exp=new_exp[:-1]
    #
    #         print "post trim ",new_exp
    #
    #         self.cleaned_data["RC_Experience"]=new_exp
