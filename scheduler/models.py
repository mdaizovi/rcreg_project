#scheduler.models
from django.db import models
from django.db.models import Q,F
from django.db import connection as dbconnection
#print "dbc0:", len(dbconnection.queries)
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.urlresolvers import reverse#for absolute url #https://docs.djangoproject.com/en/1.8/ref/urlresolvers/#django.core.urlresolvers.reverse
#from datetime import datetime, timedelta
import datetime
from datetime import timedelta
import string
import collections
#from django.db.models.signals import pre_save, post_save,post_delete
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from con_event.models import Matching_Criteria, Con, Registrant, LOCATION_TYPE,LOCATION_CATEGORY,GENDER,SKILL_LEVEL_CHG, SKILL_LEVEL_TNG,SKILL_LEVEL,SKILL_LEVEL_GAME
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME
from django.db.models.signals import pre_save, post_save,post_delete,pre_delete
from scheduler.signals import adjust_captaining_no,challenge_defaults,delete_homeless_roster_chg,delete_homeless_roster_ros,delete_homeless_chg
from scheduler.app_settings import CLOSE_CHAL_SUB_AT
from copy import deepcopy
from swingtime.conf.swingtime_settings import TIMESLOT_INTERVAL,TIMESLOT_START_TIME,TIMESLOT_END_TIME_DURATION

#not to self: will have to make ivanna choose 30/60 when scheduling
COLORS=(("Black","Black"),("Beige or tan","Beige or tan"),("Blue (aqua or turquoise)","Blue (aqua or turquoise)"),("Blue (dark)","Blue (dark)"),("Blue (light)","Blue (light)"),("Blue (royal)","Blue (royal)"),
    ("Brown","Brown"),("Burgundy","Burgundy"),("Gray/Silver","Gray/Silver"),("Green (dark)","Green (dark)"),("Green (grass)","Green (grass)"),("Green (lime)","Green (lime)"),("Green (olive or camo pattern)","Green (olive or camo pattern)"),
    ("Orange","Orange"),("Pink (hot)","Pink (hot)"),("Pink (light)","Pink (light)"),("Purple","Purple"),("Red","Red"),("White","White"),("Yellow/gold","Yellow/gold"))
GAMETYPE=(('3CHAL','30 minute Challenge'),('6CHAL','60 minute Challenge'),('36CHAL','30 or 60 minute Challenge'),('6GAME','60 min REGULATION or SANCTIONED Game (between two existing WFTDA/MRDA/RCDL/USARS teams)'))
#GAMETYPE=(('3CHAL','30 minute Challenge'),('6CHAL','60 minute Challenge'),('36CHAL','30 or 60 minute Challenge'))
RULESET=(('WFTDA','WFTDA'),('MRDA','MRDA'),('RDCL','RDCL'),('USARS','USARS'),('Other','Other'))
INTEREST_RATING=((0,'NA'),(1, '1: Very Low Interest'), (2, '2: Somewhat Low Interest'),(3, '3: Medium'), (4,'4: Somewhat High Interest'), (5, '5: Very High Interest'))
SESSIONS_TR=((1,1),(2,2),(3,3),(4,4),(5,5))
DURATION=(('0.75','45 minutes'),('1','1 Hour'),('1.5', 'Hour and a Half (90 minutes)'),('2','2 Hours (120 minutes)'))
DEFAULT_ONSK8S_DURATION='2'
DEFAULT_OFFSK8S_DURATION='1'
DEFAULT_CHALLENGE_DURATION='0.75'
DEFAULT_SANCTIONED_DURATION='1.5'
GAME_CAP = 20
DEFAULT_REG_CAP=60
DEFAULT_AUD_CAP=10
SKILL_INTEREST_DICT={'AO':5, 'AB':4,'BO':3,'BC':2,'CO':1,'ABC':1,'A':5,'B':3,"C":2,"D":1}


class Venue(models.Model):
    name=models.CharField(max_length=50, unique=True)

    def __unicode__(self):
       return self.name

    class Meta:
        ordering=('name',)

class Location(models.Model):
    venue=models.ForeignKey(Venue,on_delete=models.PROTECT)#https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.ForeignKey.on_delete
    name=models.CharField(max_length=50)
    abbrv=models.CharField(max_length=50, null=True, blank=True)
    location_type=models.CharField(max_length=50, choices=LOCATION_TYPE)
    location_category=models.CharField(max_length=50, null=True, blank=True,choices=LOCATION_CATEGORY)

    def __unicode__(self):
       return "%s, %s" % (self.name, self.venue.name)

    def is_free(self, start_time,end_time):
        """Checks to see if Location has any Occurrences for the time between start and end provided."""
        from swingtime.models import Occurrence
        qs = list(Occurrence.objects.filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
            location=self))

        if len(qs)>0:
            return False
        else:
            return True

    def empty_times(self,date_list,duration):
        """Checks to see when during a date range, probably con date range, in which there is nothing going on,
        not even empty occurrence, for time period.
        returns list of DateTime tuples: (start time, end time)"""
        ###this can probably be used to significantly speed up make dumy occurrences
        from swingtime.models import Occurrence
        dur_delta=int(float(duration)*60)

        if len(date_list)<=0:
            return empty_times
        else:
            d1=date_list[0]
            d2=date_list[-1]
            period_start=datetime.datetime(year=d1.year, month=d1.month, day=d1.day,hour=TIMESLOT_START_TIME.hour)
            period_end=datetime.datetime(year=d2.year, month=d2.month, day=d2.day,hour=TIMESLOT_START_TIME.hour)+TIMESLOT_END_TIME_DURATION
            possible_times=[]

            current_start=period_start
            current_end=period_start+datetime.timedelta(minutes=dur_delta)
            while current_end<=period_end:
                potential_slot=(current_start,current_end)
                #print("potential: ",potential_slot)
                possible_times.append(potential_slot)
                current_start+=TIMESLOT_INTERVAL
                current_end+=TIMESLOT_INTERVAL

            #print("possible_times len",len(possible_times))

            all_os=list(Occurrence.objects.filter(start_time__gte=period_start, end_time__lte=period_end,location=self))
            all_os.sort(key=lambda x: x.start_time)
            #print("all_os len",len(all_os))
            taken_times=[]

            for o in all_os:
                #print("o: ",o)
                this_set=[]
                blockstart=o.start_time+TIMESLOT_INTERVAL-datetime.timedelta(minutes=dur_delta)
                blockend=o.end_time
                #print("blockstart",blockstart)
                cs=blockstart
                ce=blockstart+datetime.timedelta(minutes=dur_delta)

                while (cs<blockend):
                    time_tup=(cs,ce)
                    #print("time_tup: ",time_tup)
                    this_set.append(time_tup)
                    ce+=TIMESLOT_INTERVAL
                    cs+=TIMESLOT_INTERVAL
                #print("this_set: ",this_set)
                for t in this_set:
                    if t in possible_times:
                        #print("about to remove ",t)
                        possible_times.remove(t)
                #print("O Round: possible_times len",len(possible_times))

        #print("possible_times len",len(possible_times))
        return possible_times

    class Meta:
        #ordering=('abbrv','venue','name')
        ordering=('venue','name')
        unique_together = ('name','venue')


class Roster(Matching_Criteria):
    participants=models.ManyToManyField(Registrant, blank=True)
    cap=models.IntegerField(null=True, blank=True)

    registered=models.OneToOneField("Training", related_name="registered",null=True, blank=True)
    auditing=models.OneToOneField("Training", related_name="auditing",null=True, blank=True)

    #only for challenges
    name=models.CharField(max_length=200,null=True, blank=True)
    captain=models.ForeignKey(Registrant,related_name="captain",null=True, blank=True,on_delete=models.SET_NULL)#maybe I should allow this to be deleted if registrant is deleted?
    color=models.CharField(max_length=100,null=True, blank=True, choices=COLORS)
    can_email=models.BooleanField(default=True)

    internal_notes= models.TextField(null=True,blank=True)

    def __unicode__(self):
        if self.name:
            return "%s %s" %(self.name, self.con)
        else:
            return "unnamed team"

    def save(self, *args, **kwargs):
        '''custom functions: removes non-ascii chars and punctuation from names, colors'''
        string_fields=['name']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                cleaned_att=ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)

        if self.internal_notes:
            cleaned_notes=ascii_only(self.internal_notes)
            self.internal_notes=cleaned_notes

        if self.captain:
            try:#so it won't freal out the first time, before first save
                if self.captain not in self.participants.all():
                    self.participants.add(self.captain)
            except:
                pass
        super(Roster, self).save()

    def criteria_conflict(self):
        '''nearly identical to Registrant method of the same name, jsut w/ skater/roster roles reversed'''
        problem_criteria=[]
        potential_conflicts=[]
        captain_conflict=False
        genders_allowed=self.genders_allowed()
        skills_allowed=self.skills_allowed()
        def capt_confl(problem_criteria,potential_conflicts,captain_conflict):
            if self.captain and (self.captain.gender not in genders_allowed):
                captain_conflict=True
                if "gender" not in problem_criteria:
                    problem_criteria.append("gender")
                    if self.captain not in potential_conflicts:
                        potential_conflicts.append(self.captain)
            if self.captain and (self.captain.skill not in skills_allowed):
                captain_conflict=True
                if "skill" not in problem_criteria:
                    problem_criteria.append("skill")
                if self.captain not in potential_conflicts:
                    potential_conflicts.append(self.captain)
            return problem_criteria,potential_conflicts,captain_conflict

        try:
            participants=list(self.participants.all())
            if len(participants)>0:
                for skater in list(self.participants.all()):
                    if skater.gender not in genders_allowed:
                        if "gender" not in problem_criteria:
                            problem_criteria.append("gender")
                        if skater not in potential_conflicts:
                            potential_conflicts.append(skater)
                        if self.captain and skater==self.captain:
                            captain_conflict=True
                    if skater.skill not in skills_allowed:
                        if "skill" not in problem_criteria:
                            problem_criteria.append("skill")
                        if skater not in potential_conflicts:
                            potential_conflicts.append(skater)
                        if self.captain and skater==self.captain:
                            captain_conflict=True
            else:
                problem_criteria,potential_conflicts,captain_conflict=capt_confl(problem_criteria,potential_conflicts,captain_conflict)
        except:#if no such thing as self.participants.all()
            problem_criteria,potential_conflicts,captain_conflict=capt_confl(problem_criteria,potential_conflicts,captain_conflict)

        if len(potential_conflicts)>0:
            return problem_criteria,potential_conflicts,captain_conflict
        else:
            return None,None,captain_conflict

    def conflict_sweep(self):
        '''nearly identical to Registrant method of the same name, jsut w/ skater/roster roles reversed
        calls criteria_conflict, removes from any rosters that have conflicts,
        including removing self as captain, making challenges unconfirmed
        ONLY WRITTEN FOR CHALLENGE, NOT TRAINING, DO LATER'''
        problem_criteria,potential_conflicts,captain_conflict=self.criteria_conflict()
        if not captain_conflict:
            if potential_conflicts:
                for skater in potential_conflicts:
                    self.participants.remove(skater)
            return True
        else:
            return False


    def has_number_dupes(self):
        '''checks to see if same sk8number is in roster twice. Checks stirng, not int.
        So as written right now, 03 is different from 3 is different from <3
        But I don't like how written because it will run 20x per roster. rewrite or don't use?'''
        numbers=[]
        dupes=[]
        for s in self.participants.all():
            if s.sk8number in numbers:
                dupes.append(s.sk8number)
            numbers.append(s.sk8number)

        if len(dupes)>0:#because an empty list still returns True
            number_dupes=dupes
        else:
            number_dupes=False

        return number_dupes

    def get_maxcap(self):
        '''checks is roster has a cap cap. If not, supplies defaults listed at top of file'''
        if self.cap:
            maxcap=self.cap
        else:
            maxcap = GAME_CAP

        return maxcap

    def spacea(self):
        '''gets maxcap (see above), checks is participants are fewer'''
        maxcap=self.get_maxcap()
        spacea=maxcap-self.participants.count()

        if spacea>0:
            return spacea
        else:
            return False

    def add_sk8er_challenge(self, skater_pk):
        skater_added=None
        add_fail=None
        if self.spacea():
            try:
                try:
                    skater_added=Registrant.objects.get(pk=skater_pk)
                    self.participants.add(skater_added)
                    self.save()
                except:
                    add_fail=Registrant.objects.get(pk=skater_pk)
            except:
                pass
        else:
            add_fail=Registrant.objects.get(pk=skater_pk)

        return skater_added,add_fail

    def remove_sk8er_challenge(self, skater_pk):
        skater_remove=None
        remove_fail=None
        try:
            try:
                skater_remove=Registrant.objects.get(pk=skater_pk)
                if skater_remove != self.captain:
                    self.participants.remove(skater_remove)
                    self.save()
                else:
                    remove_fail=skater_remove
            except:
                remove_fail=Registrant.objects.get(pk=skater_pk)
        except:
            pass

        return skater_remove,remove_fail

    def opponent_skills_allowed(self):
        allowed=[]
        skillphabet=["A","AB","B","BC","C"]
        if self.skill:
            #print self, self.skill
            skill_index=skillphabet.index(self.skill_display())
            for i in range(skill_index-1,skill_index+2):
                if i>=0 and i<len(skillphabet):
                    allowed.append(skillphabet[i])
        else:
            allowed.append( self.skill_display() )
        #print self, allowed
        return allowed

    def genders_allowed(self):
        if self.gender=='NA/Coed':
            allowed=["Female","Male","NA/Coed"]
        else:
            allowed=["NA/Coed",self.gender]
        return allowed

    def intls_allowed(self):
        if self.intl is True:
            allowed=[True]
        else:
            allowed=[True,False,None]
        return allowed

    def passes_allowed(self):

        #this shouldn't be here anymore, w' new trainingroster strucutre
        # if self.registered or self.auditing:#this is a training
        #     if self.registered:
        #         training=self.registered
        #     elif self.auditing:
        #         training=self.auditing
        #
        #     if training.onsk8s:
        #         allowed=['MVP']
        #     else:
        #         allowed=['MVP','Skater','Offskate']
        #
        # #elif self.captain or self.color:#this is a challenge
        # else:#this is a challenge
        #     allowed=['MVP','Skater']

        #return allowed
        return ['MVP','Skater']

    def passes_tooltip_title(self):
        pass_list=self.passes_allowed()
        pass_string=""
        if len(pass_list)>1:
            if len(pass_list)>2:
                for item in pass_list[:-1]:
                    pass_string+=item+", "
            else:
                pass_string+=pass_list[0]
            pass_string+=" or "+pass_list[-1]
        else:
            pass_string=pass_list[0]

        # if self.registered:
        #     base_str=self.registered.onsk8s_tooltip_title()
        # elif self.auditing:
        #     base_str=self.auditing.onsk8s_tooltip_title()
        # else:
        #     base_str=""

        tooltip_title = base_str+(" Registrant must have %s pass in order to register"%(pass_string))
        return tooltip_title

    def editable_by(self):
        '''returns list of Users that can edit Roster
        this is for adding/removing roster participants, so coaches actually don't have this permission,
        they are only true in activity.editable_by'''

        allowed_editors=list(User.objects.filter(groups__name__in=[BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME]))

        if self.captain:#this is so NSOs can't edit training rosters. COULD BE PROBLEM is captain freaks out and leaves challenge? unlikely, and boss ladies will still be able to fix
            allowed_editors.append(self.captain.user)
            allowed_editors+=list(User.objects.filter(groups__name__in=['NSO']))

        return allowed_editors

    def nearly_homeless(self):
        '''This is for reject warning, to check if rejecting this challenge will delete roster.
        Mostly for Game rosters, kinda ovbious for Challenge Rosters'''
        r1=list(self.roster1.all())
        r2=list(self.roster2.all())
        rs=r1+r2
        if len(rs)<=1:
            return True
        else:
            return False

    def is_homeless(self):
        '''This is for reject warning, to check if rejecting this challenge will delete roster.
        Mostly for Game rosters, kinda ovbious for Challenge Rosters'''
        r1=list(self.roster1.all())
        r2=list(self.roster2.all())
        rs=r1+r2
        if len(rs)<=0:
            return True
        else:
            return False

    def coed_beginner(self):
        #maybe write something simialr for minimum contact skills?
        if self.gender=='NA/Coed':
            forbidden_skills=[None,False,'C','CO','BC','ABC']
            if self.skill in forbidden_skills:
                coed_int_str="Coed teams have a minimum skill level of Intermediate."
                if self.captain and self.captain.skill and self.captain.skill in ["B","BO","A","BO"]:#if captain is intermediate or above
                    self.skill="BO"
                    coed_int_str+=" In order to remain coed, the skill level has been raised to Intermediate. If you'd like to include a lower skill level, please change team gender first."
                else:
                    if self.captain.gender:
                        self.gender=self.captain.gender
                    else:
                        self.gender="Female"
                    coed_int_str+=" Because your skill is not Intermediate, team Gender has been assigned."
                #self.save()
                return coed_int_str

            else:
                return False
        else:
            return False

    def restore_defaults(self):
        self.captain=None
        self.participants.clear()
        self.name=None
        self.color=None
        self.can_email=True
        self.save() #save here, or elsewhere?

    def defaults_match_captain(self):
        if self.captain:
            self.gender=self.captain.gender
            cap_skill=str(self.captain.skill)
            self.skill=cap_skill+"O"
            self.con=self.captain.con
            self.save()
        else:
            self.restore_defaults()#saved internally

    def clone_roster(self):
        """Clones team, including roster. Not meant for trainings, just challenge rosters.
        Makes a new one, whcih might be inapporpriate for purposes. To make existing roster mimic other, see mimic_roster"""
        clone=deepcopy(self)
        clone.pk=None
        clone.id=None
        clone.internal_notes=None
        clone.save()
        clone.participants.add(*self.participants.all())#strange note: before save, clone has self's participants. but after save, loses them.
        #http://stackoverflow.com/questions/6346600/duplicate-django-objects-with-manytomanyfields
        clone.save()
        return clone

    def mimic_roster(self,original):
        """makes self look just like original roster, except for pk, of course."""
        for attr in ['cap','name','captain','color','can_email']:
            value=getattr(original,attr)
            setattr(self, attr, value)
        self.save()
        self.participants.add(*original.participants.all())
        self.save()

    def get_edit_url(self):
        return reverse('scheduler.views.edit_roster', args=[str(self.pk)])

    class Meta:
        ordering=("-con__start",'name','captain')
        #unique_together = ('name','con','captain')#I think this is my original sin. fuck me.

post_save.connect(delete_homeless_roster_ros, sender=Roster)
pre_delete.connect(adjust_captaining_no, sender=Roster)

class Activity(models.Model):
    #fields that are shared between challenge and training
    name=models.CharField(max_length=200)
    con = models.ForeignKey(Con,on_delete=models.PROTECT)#https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.ForeignKey.on_delete
    location_type=models.CharField(max_length=30, choices=LOCATION_TYPE)
    RCaccepted=models.BooleanField(default=False)
    RCrejected=models.BooleanField(default=False)
    created_on=models.DateTimeField(default=timezone.now)
    #because durationfileds are buggy in 1.8
    duration=models.CharField(max_length=30,choices=DURATION,null=True, blank=True)
    interest=models.IntegerField(null=True, blank=True,choices=INTEREST_RATING)

    internal_notes= models.TextField(null=True,blank=True)
    communication = models.TextField(null=True,blank=True)

    def is_a_challenge(self):
        """ Tests to see if is Challenge. If else, probably a Training.
        Just wanted to stop repeating self w/ hasattr, in case I ever change fields that dictate which it is"""
        if hasattr(self, 'roster1') or hasattr(self, 'roster2'):
            return True
        else:
            return False

    def is_a_training(self):
        """ Tests to see if is Training If else, probably a Challenge.
        Just wanted to stop repeating self w/ hasattr, in case I ever change fields that dictate which it is"""
        if hasattr(self, 'coach'):
            return True
        else:
            return False

    def get_default_interest(self):
        """if chal, gets average of teams skill.
        if training, gerts average of coach skill
        to estimate interest my skill"""
        skill_list=[]
        #print self
        if self.is_a_challenge():
            if self.is_a_game:
                skill_list.append(5)
            else:
                for r in [self.roster1,self.roster2]:
                    if r and r.skill:
                        #print r , r.skill
                        thisskill=SKILL_INTEREST_DICT.get(r.skill)
                        if thisskill:
                            skill_list.append(thisskill)
        if self.is_a_training():
            if self.skill:
                thisskill=SKILL_INTEREST_DICT.get(self.skill)
                if thisskill:
                    skill_list.append(thisskill)
            for c in self.coach.all():
                #print c
                r=c.user.get_most_recent_registrant()
                #print r, r.skill
                thisskill=SKILL_INTEREST_DICT.get(r.skill)
                if thisskill:
                    skill_list.append(thisskill)

        if len(skill_list)>1:
            def_skill=sum(skill_list) / float(len(skill_list))
        else:
            def_skill=3
        return def_skill


    def get_figurehead_registrants(self):
        """Determines if is Training or Challange. If former, gets coaches. If latter, gets captains."""
        #select/prefetch brought it form 5 db hits to 3 on trainings
        figureheads=[]
        if self.is_a_training():
            for c in self.coach.select_related('user').prefetch_related('user__registrant_set').all():
                for r in c.user.registrant_set.select_related('con').all():
                    if r.con==self.con:
                        figureheads.append(r)
        elif self.is_a_challenge():
            for r in [self.roster1,self.roster2]:
                if r and r.captain:
                    figureheads.append(r.captain)
        return figureheads

    def get_figurehead_display(self):
        fs=self.get_figurehead_registrants()
        fstr=""
        index=1
        for f in fs:
            if index>1:
                fstr+=" & "
            if f.sk8name:
                fstr+=f.sk8name
            else:
                fstr+=f.name
            index+=1
        return fstr

    def get_figurehead_blackouts(self):
        """Gets Blackouts for activity, from all coaches or captains, but not participants."""
        from con_event.models import Blackout
        figureheads=self.get_figurehead_registrants()
        b_outs=list(Blackout.objects.filter(registrant__in=figureheads))
        return b_outs

    def editable_by(self):
        '''returns list of Users that can edit Activity
        keep in mind being captain of EITHER team makes this True
        Also, boss ladies, but no NSOs or Volunteers'''
        allowed_editors=list(User.objects.filter(groups__name__in=[BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME]))

        figureheads=self.get_figurehead_registrants()#see above. Registrants of captains and coaches.
        for f in figureheads:
            allowed_editors.append(f.user)

        return allowed_editors

    def participating_in(self):
        '''returns list of Registrants that are on either skating/participating roster, or are Coach
        For use in Scheduling as well as seeing Communication between NSO/skaters'''
        #no prefetch/select is 7 db hits for a training, trimmed it down to 4
        participating=[]
        #print "dbcP:", len(dbconnection.queries)
        if self.is_a_training():
            for c in self.coach.select_related('user').all():
                for reg in c.user.registrant_set.select_related('con').all():
                    if reg.con==self.con:
                        participating.append(reg)

            #doesn't work anymore, not sure if can reconfigure w/ new trainingroster structure
            # for ros in [self.registered, self.auditing]:
            #     if ros:
            #         for sk8 in ros.participants.all():
            #             participating.append(sk8)

        elif self.is_a_challenge():
            for ros in [self.roster1,self.roster2]:
                if ros:
                    for sk8 in ros.participants.all():
                        participating.append(sk8)
                    if ros.captain and ros.captain not in participating:
                        participating.append(ros.captain)
        #print "dbcP6:", len(dbconnection.queries)
        return participating

    def possible_locations(self):
        """Gets locaiton type of activity, returns list of specific locations it can be in, for that Con
        Will prob need to write anoter further refining, splitting up competition and training tracks"""
        venues=self.con.venue.prefetch_related('location').all()

        if self.location_type =='Flat Track':
            if self.is_a_training():#if this is a training
                return list(Location.objects.filter(venue__in=venues, location_type='Flat Track', location_category="Training"))
            elif self.is_a_challenge():
                if self.is_a_game or float(self.duration)>=1:#has to be in C1
                #should I hard-code 60 min only goes to C1, or should I jsut let it be? or figer out a better way?
                    return list(Location.objects.filter(venue__in=venues, location_type='Flat Track', location_category="Competition Any Length"))
                else:#can be n C1 or C2
                    return list(Location.objects.filter(venue__in=venues, location_type='Flat Track', location_category__in=["Competition Half Length Only","Competition Any Length"]))

        elif self.location_type == 'EITHER Flat or Banked Track':
            if self.is_a_training():#if this is a training
                return list(Location.objects.filter(location_category__in=["Training","Training or Competition"], venue__in=venues, location_type__in=['Flat Track','Banked Track']))
            elif self.is_a_challenge():
                return list(Location.objects.filter(location_category__in=["Training or Competition","Competition Half Length Only","Competition Any Length"],venue__in=venues, location_type__in=['Flat Track','Banked Track']))
        else:
            return list(Location.objects.filter(venue__in=venues, location_type=self.location_type))


    def dummy_occurrences(self,level,makedummies):
        """Makes unsaved Occurrence objects for all possible location time combos for activity
        EDIT April 22 2016: also gathers possible empty occurrances"""
        #this works, but it makes about 2500 on my first test run.
        from swingtime.models import Occurrence
        #print("dummy occurrences, level ",level)
        #empties=[]
        dummies=[]
        pls=self.possible_locations()
        if self.interest:
            proxy_interest=self.interest
        else:
            proxy_interest=self.get_default_interest()

        #print("proxy_interest 1",proxy_interest)
        #print "possible locations: ",pls
        if self.is_a_training():#if this is a training
            proxy_interest=abs(6-proxy_interest)#to make high demand classes in low interest timeslots and vice versa
            challenge=None
            training=self
        elif self.is_a_challenge():
            challenge=self
            training=None
        #print("proxy_interest 2",proxy_interest)
        duration=float(self.duration)
        dur_delta=int(duration*60)

        #print "dur_delta= ",dur_delta
        date_range=self.con.get_date_range()
        #ideas not yet incorporateD: interwt matching, duration matches durdelta
        base_q=Occurrence.objects.filter(challenge=None,training=None,location__in=pls,start_time__gte=self.con.start, end_time__lte=self.con.end)

        if level==1:
            base_q=base_q.filter(interest=proxy_interest).filter(end_time=F('start_time') + timedelta(minutes=dur_delta))
        elif level==2:
            ilist=[int(proxy_interest)-1,int(proxy_interest),int(proxy_interest)+1]
            base_q=base_q.filter(interest__in=ilist).filter(end_time=F('start_time') + timedelta(minutes=dur_delta))
        #else if is 3 or, no extra filter

        empties=list(base_q)
# ##########works, but is time consuming. But don't want to optimize if Ivanna doesn't care and never uses
        if makedummies:
            for d in date_range:
                day_start=datetime.datetime(year=d.year, month=d.month, day=d.day,hour=TIMESLOT_START_TIME.hour)
                day_end=day_start+TIMESLOT_END_TIME_DURATION
                slot_start=day_start
                slot_end=slot_start+datetime.timedelta(minutes=dur_delta)

                while slot_end<day_end:
                    for l in pls:
                        if l.is_free(slot_start,slot_end):
                            o=Occurrence(start_time=slot_start,end_time=slot_end,location=l,challenge=challenge,training=training)
                            dummies.append(o)

                    slot_start+=TIMESLOT_INTERVAL
                    slot_end+=TIMESLOT_INTERVAL
                    ###################
        # # I thought this would be faster, but actually seems slower. 11 secs tuens to 14, 60 to 80.
        # if makedummies:
        #     for l in pls:
        #         possibles=l.empty_times(date_range,duration)
        #         for p in possibles:
        #             o=Occurrence(start_time=p[0],end_time=p[1],location=l,challenge=challenge,training=training)
        #             dummies.append(o)

        return [empties,dummies]

    # def sched_conflict_split(self):
    #     """Makes dict of smaller dicts, smaller dict has occurrence as k, conflicts and v.
    #     Later look for the k,v pair that is an occurrence and an empty dict to find ones w/ no conflict."""
    #     print "about to start sched_conflict_split"
    #     occurrences=self.dummy_occurrences()
    #     conflict={"blackout_conflict":[],"figurehead_conflict":[],"participant_conflict":[],"no_conflict":[]}
    #
    #     for o in occurrences:
    #         blackout_conflict=o.blackout_conflict()
    #         if blackout_conflict:
    #             temp_list=conflict.get("blackout_conflict")
    #             temp_list.append(o)
    #             conflict["blackout_conflict"]=list(temp_list)
    #         figurehead_conflict=o.figurehead_conflict()
    #         if figurehead_conflict:
    #             temp_list=conflict.get("figurehead_conflict")
    #             temp_list.append(o)
    #             conflict["figurehead_conflict"]=list(temp_list)
    #         participant_conflict=o.participant_conflict()
    #         if participant_conflict:
    #             temp_list=conflict.get("blackout_conflict")
    #             temp_list.append(o)
    #             conflict["participant_conflict"]=list(temp_list)
    #         if not blackout_conflict and not figurehead_conflict and not participant_conflict:
    #             temp_list=conflict.get("no_conflict")
    #             temp_list.append(o)
    #             conflict["no_conflict"]=list(temp_list)
    #     print "finished sched_conflict_split"
    #     return conflict

    def sched_conflict_score(self,level,makedummies):
        """Takes in activity, makes list of dummy occurrances. checks each one for schedule conflicts,
        scores them so that each Blackout is worth 100 pts, Figurehead 10, Participant 1.
        Returns ordered dict, w/ key as score, v as list of occurrences that match score, sorted 0-highest
        NEW: may remove Os depending on level"""
        #print "about to start sched_conflict_score"
        odict_list=[]
        if self.is_a_training():
            training=self
        else:
            training=None
        if self.is_a_challenge():
            challenge=self
        else:
            challenge=None
        #print("sched_conflict_score ",training,challenge)

        if int(level)<2:
            max_score=0
        elif int(level)==2:
            max_score=99
        else:
            max_score=999999999999999999 #arbitrary relaly big number

        #for o in dummy_occurrences:
        #print("sched_conflict_score level is ",level)

        for olist in list(self.dummy_occurrences(level=level,makedummies=makedummies)):
            #print "sched conflict score olist:",olist
            if len(olist)>0:
                #print "more than 1!"
                conflict={}
                #print "olist: ",olist
                for o in olist:
                    #don't save, this is to make figruehead registrants work
                    o.training=training
                    o.challenge=challenge
                    score=0
                    blackout_conflict=o.blackout_conflict()
                    if blackout_conflict:
                        #print "blackout_conflict: ",len(blackout_conflict),blackout_conflict
                        this_score=len(blackout_conflict)*100
                        #print "blackout score: ",this_score
                        score+=this_score

                    figurehead_conflict=o.figurehead_conflict()
                    if figurehead_conflict:
                        #print "figurehead_conflict: ",len(figurehead_conflict),figurehead_conflict
                        this_score=len(figurehead_conflict)*10
                        #print "figurehead score: ",this_score
                        score+=this_score

                    participant_conflict=o.participant_conflict()
                    if participant_conflict:
                        #print "participant_conflict: ",len(participant_conflict),participant_conflict
                        this_score=len(participant_conflict)*1
                        #print "participant score: ",this_score
                        score+=this_score

                    if score not in conflict:
                        conflict[score]=[o]
                    else:
                        this_list=conflict.get(score)
                        this_list.append(o)
                        conflict[score]=list(this_list)
            else:#if empty list, otherwise uses last conflict and returns wrond occurrence
                conflict={}

            score_list=list(conflict.keys())
            score_list.sort()
            odict  = collections.OrderedDict()
            #print len(odict)

            for score in score_list:
                if score<=max_score:
                    temp_list=conflict.get(score)
                    odict[score]=list(temp_list)

            #print odict.keys()
            odict_list.append(odict)

        return odict_list

    def find_level_slots(self):
        """Experimental function to find or make matching occurrences for auto scheduler.
        Precedence: 1-try to FIND Level 1 match, if not, try to MAKE Level 1 match, if not, find Level 2, so on...
        Differs from manual schedule levels slighty in that all levels here require right duration"""
        #print"running find level slots for ",self
        from swingtime.models import Occurrence
        if self.interest:
            proxy_interest=self.interest
        else:
            proxy_interest=self.get_default_interest()
        if self.is_a_training():#if this is a training
            proxy_interest=abs(6-proxy_interest)#to make high demand classes in low interest timeslots and vice versa
            challenge=None
            training=self
        elif self.is_a_challenge():
            challenge=self
            training=None

        dur_delta=int(float(self.duration)*60)
        pls=self.possible_locations()

        #print "proxy interest is ",proxy_interest
        #could get  possible_times=l.empty_times(date_list,duration)   for l in pls

        #base_q is base level requirements: made but empty, right time, right location Don't know about interest or conflicts.
        base_q=list(Occurrence.objects.filter(challenge=None,training=None,location__in=pls,end_time=F('start_time') + timedelta(minutes=dur_delta)))
        level1find=[]
        level1halffind=[]#this is for if the interest doesn't quite match but still no conflicts
        level2find=[]
        level3find=[]

        for o in base_q:#sor list rather than multiple queries
            #print o.start_time,o.end_time, o.interest,o.location

            if o.interest and (abs( float(o.interest)-float(proxy_interest) )<1):
            #if o.interest and float(o.interest)==float(proxy_interest): #i think this causes problems w/ apprxiamted decimal nterest
                level1find.append(o)
                #print"putting in level1"
            elif o.interest and (abs( float(o.interest)-float(proxy_interest) )<2):
                level2find.append(o)
                #print"putting in level2"
            else:
                level3find.append(o)
                #print"putting in level3"

        #print self, "level1find len ",len(level1find),"level2find len ",len(level2find),"level3find len ",len(level3find)

        #still need conflict sort
        for l in [level1find,level2find]:
            for o in l:
                o.challenge=challenge#don't save!
                o.training=training#DON'T SAVE!
                score=0
                blackout_conflict=o.blackout_conflict()
                if blackout_conflict:
                    #print "blackout_conflict: ",len(blackout_conflict),blackout_conflict
                    this_score=len(blackout_conflict)*100
                    #print "blackout score: ",this_score
                    score+=this_score

                figurehead_conflict=o.figurehead_conflict()
                if figurehead_conflict:
                    #print "figurehead_conflict: ",len(figurehead_conflict),figurehead_conflict
                    this_score=len(figurehead_conflict)*10
                    #print "figurehead score: ",this_score
                    score+=this_score

                participant_conflict=o.participant_conflict()
                if participant_conflict:
                    #print "participant_conflict: ",len(participant_conflict),participant_conflict
                    this_score=len(participant_conflict)*1
                    #print "participant score: ",this_score
                    score+=this_score

                #print"Score:  ",score,o.start_time,o.end_time, o.interest,o.location
                if score > 99:
                    if o in level1find:
                        #print "removing from level1"
                        level1find.remove(o)
                    if o in level2find:
                        #print "removing from level2"
                        level2find.remove(o)
                    level3find.append(o)
                    #print "put in level3"
                elif score <= 99 and score > 0:
                    if o in level1find:
                        #print "removing from level1"
                        level1find.remove(o)

                    if o not in level2find:
                        #print "putting in level3"
                        level2find.append(o)

                elif score <=0: #if there's no ocnflict but it's still a +/- 1 interest match
                    #print "no conflict but still a maybe +/- interest match"
                    if o in level2find:
                        level2find.remove(o)
                        #print"remvoed form l2"
                    level1halffind.append(o)
                    #print"put in level half"

                o.challenge=None#back to blank
                o.training=None#backto blank

        return level1find,level1halffind,level2find,level3find

    def scheduled(self):
        os=list(self.occurrence_set.all())
        return os

    def get_activity_type(self):
        """Written so can easily see if is snctioned game/chal in templates.
        Might as well throw in some training data too,
        but this was mostly written so can use Cycle template tag for both chal and train"""

        loc_str=""

        #both have location_type
        if self.location_type=='EITHER Flat or Banked Track':
            loc_str="FT or BT "
        elif self.location_type=="Flat Track":
            loc_str="FT "
        elif self.location_type=='Banked Track':
            loc_str="BT "
        elif self.location_type=='Off Skates Athletic Training':
            loc_str="Xsk8 Athletic "
        elif self.location_type=='Seminar/Conference Room':
            loc_str="Xsk8  "


        if self.is_a_training():#if this is a training
            #loc_str+=self.get_duration_display()
            loc_str+=("("+self.duration+" Hrs)")

        elif self.is_a_challenge():
            if self.gametype in ['3CHAL','6CHAL','36CHAL']:
                if self.gametype=='3CHAL':
                    loc_str+="30m"
                elif self.gametype=='6CHAL':
                    loc_str+="60m"
                elif self.gametype=='36CHAL':
                    loc_str+="30 or 60m"
                loc_str+=" Challenge"
            elif self.is_a_game or self.gametype=="6GAME":
                loc_str+="60m Reg/San Game"

        return loc_str


#maybe i should rename this to get absolute url so view on site is easier?
    def get_view_url(self):
        if self.is_a_training():#if this is a training
            from scheduler.views import view_training
            return reverse('scheduler.views.view_training', args=[str(self.pk)])

        elif self.is_a_challenge():
            from scheduler.views import view_challenge
            return reverse('scheduler.views.view_challenge', args=[str(self.pk)])

    def get_edit_url(self):
        if self.is_a_training():
            from scheduler.views import edit_training
            return reverse('scheduler.views.edit_training', args=[str(self.pk)])

        elif self.is_a_challenge():
            #I think this might actually be stupid
            from scheduler.views import edit_challenge
            return reverse('scheduler.views.edit_challenge', args=[str(self.pk)])

    def get_sched_assist_url(self):
        if self.is_a_training():
            from swingtime.views import sched_assist_tr
            return reverse('swingtime.views.sched_assist_tr', args=[str(self.pk)])
        elif self.is_a_challenge():
            from swingtime.views import sched_assist_ch
            return reverse('swingtime.views.sched_assist_ch', args=[str(self.pk)])

    class Meta:
        #ordering=('-created_on',)#not sure if abstract can be ordered?
        abstract = True

class ChallengeManager(models.Manager):

    def submission_full(self,con):
        """If we have too many challenges submitted this year, returns true. Else, false
        Excludes Games from count"""
        submissions=list(Challenge.objects.filter(con=con).exclude(submitted_on=None,is_a_game=True))
        if len(submissions)<CLOSE_CHAL_SUB_AT:
            return False
        else:
            return True

class Challenge(Activity):
    roster1=models.ForeignKey(Roster, related_name="roster1", null=True,blank=True,on_delete=models.SET_NULL)
    roster2=models.ForeignKey(Roster, related_name="roster2", null=True,blank=True,on_delete=models.SET_NULL)
    captain1accepted=models.BooleanField(default=True)
    captain2accepted=models.BooleanField(default=False)
    roster1score=models.IntegerField(null=True, blank=True)
    roster2score=models.IntegerField(null=True, blank=True)
    ruleset=models.CharField(max_length=30, choices=RULESET, default=RULESET[0][0])
    gametype=models.CharField(max_length=250, choices=GAMETYPE, default=GAMETYPE[0][0])
    submitted_on=models.DateTimeField(null=True, blank=True)
    is_a_game=models.BooleanField(default=False)
    objects = ChallengeManager()

    def __unicode__(self):
       return "%s: %s" %(self.name, self.con)

    def save(self, *args, **kwargs):

        string_fields=['internal_notes','communication']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                #NOTEE: I'm allowing punctuation in name and description, hope this doesn't bite me
                #usualy I strip all punctuation
                cleaned_att=ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        #I should ave made the name a property. This is stupid. Maybe change later?
        if self.roster1 and self.roster1.name:
            name1=self.roster1.name
        else:
            name1="?"
        if self.roster2 and self.roster2.name:
            name2=self.roster2.name
        else:
            name2="?"
        self.name= "%s vs %s" % (name1,name2)

        #moved duration and gametype to presave challenge_defaults signalF

        super(Challenge, self).save()

    def roster4registrant(self,registrant):
        """takes in registrant, returns which team they're on"""
        if registrant in self.roster1.participants.all():
            return roster1
        elif registrant in self.roster2.participants.all():
            return roster2
        else:
            return None

    def rosterreject(self,roster):
        """takes in roster, rejects challenge. if both have rejected, deletes challenge."""
        opposing_cap=None
        opposing=None

        if self.roster1==roster:
            self.captain1accepted=False
            if self.roster2:
                opposing=self.roster2

        elif self.roster2==roster:
            self.captain2accepted=False
            if self.roster1:
                opposing=self.roster1

        if not self.captain1accepted and not self.captain2accepted:
            for r in [self.roster1, self.roster2]:
                if r :
                    cappy=r.captain
                    #this should always run now that i made rosters unique to challenges but I'll keep just in case
                    if len(list(r.roster1.all())+list(r.roster2.all()))==1:#if this is this rosters only challange
                        print "Roster reject, deleting ",r
                        r.delete()
                    if cappy:
                        cappy.save()#to reset captain number

            if self.id and self.pk:
                self.delete()
        else:
            #set rejected roster back to defaults. gets saved in method.
            roster.restore_defaults()
            self.save()#make sure after naked roster is saved, so chal name will include ? again


    def my_team_status(self, registrant_list):
        '''takes in registrant list, tells you which team you're captaining, whether you've accepte, who your opponent is, and if they'e accepted'''
        if self.roster1 and self.roster1.captain and (self.roster1.captain in registrant_list):
            my_team=self.roster1
            opponent=self.roster2
            my_acceptance=self.captain1accepted
            opponent_acceptance=self.captain2accepted
        elif self.roster2 and self.roster2.captain and (self.roster2.captain in registrant_list):
            my_team=self.roster2
            opponent=self.roster1
            my_acceptance=self.captain2accepted
            opponent_acceptance=self.captain1accepted
        else:
            my_team=None
            opponent=None
            my_acceptance=None
            opponent_acceptance=None

        return my_team,opponent,my_acceptance,opponent_acceptance

    def replace_team(self,old_team,selected_team):
        """for changing from disposable team to Game team. Finds the team te registrant is a captain of, removes that team, puts given team in it place."""
        if self.roster1 and self.roster1==old_team:
            self.roster1=selected_team
        elif self.roster2 and self.roster2==old_team:
            self.roster2=selected_team

        #self.save()
        return old_team,selected_team

    def can_submit_chlg(self):
        """
        first checks to see if both captains have accepted.
        If yes and is a Game, can submit as long as first sub date has passed, and schedule is not final.
        If yes and is a Challenge, can submit as long as first sub date has passed and max chal cp hasn't been reached.
        """
        can_sub=False
        if self.roster1 and self.captain1accepted and self.roster2 and self.captain2accepted:
            if self.con.can_submit_chlg_by_date():
                if self.is_a_game and not self.con.sched_final:
                    can_sub= True
                elif not self.is_a_game and self.con.can_submit_chlg():
                    can_sub= True

        return can_sub

    def skill_display(self):
        """Like method of same name for Roster, makes it so I don't see A0, just A, or AB, or something more understandable
        If different for 2 rosters, returns both. otehrwise if same, 1."""
        r1skill=r2skill=display=None

        if self.roster1:
            r1skill=self.roster1.skill_display()
        if self.roster2:
            r2skill=self.roster2.skill_display()

        if r1skill and r2skill:
             if r1skill != r2skill:
                 display="%s & %s"%(r1skill,r2skill)
             else:
                 display=r1skill
        elif r1skill and not r2skill:
            display=r1skill
        elif r2skill and not r1skill:
            display=r2skill

        return display

    def skills_match(self):
        match=False
        if self.roster1 and self.roster2:
            pass

        return match


    def gender_display(self):
        """Like skill display above but w/ gender."""
        r1gen=r2gen=display=None

        if self.roster1:
            r1gen=self.roster1.gender
        if self.roster2:
            r2gen=self.roster2.gender

        if r1gen and r2gen:
             if r1gen != r2gen:
                 display="%s & %s"%(r1gen,r2gen)
             else:
                 display=r1gen
        elif r1gen and not r2gen:
            display=r1gen
        elif r2gen and not r1gen:
            display=r2gen

        return display

    class Meta:
        #insted should i make a save method that makes roster1 name v roster2 name as the name?
        ordering=('-con__start','name')
        unique_together = ('con','name','roster1','roster2')

pre_save.connect(challenge_defaults, sender=Challenge)
post_save.connect(delete_homeless_chg, sender=Challenge)
pre_delete.connect(delete_homeless_roster_chg, sender=Challenge)

class Training(Activity):
    #activity has fields: name,con,location_type,RCaccepted, created_on,duration
    coach = models.ManyToManyField('Coach', blank=True)#can't be ForeignKey bc can be multiple coaches

    skill=models.CharField(max_length=30, null=True,blank=True,choices=SKILL_LEVEL_TNG)
    onsk8s=models.BooleanField(default=True)
    contact=models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    regcap = models.IntegerField(null=True, blank=True)
    audcap = models.IntegerField(null=True, blank=True)

    sessions = models.IntegerField(default=1, choices=SESSIONS_TR)

    def __unicode__(self):
       return "%s  (%s)" %(self.name, self.con)


    def display_coach_names(self):
      #this seems to create an infinite loop somewhere
        if self.coach and self.coach.count()>0:
            coach_names=""
            for coach in self.coach.all():
                coach_names+=coach.user.first_name+", "
                cut_coach_names=coach_names[0:-2]
            return cut_coach_names
        else:
            return None

    def get_coach_registrants(self):
        """Gets all registrants for Coach, since Coach is tied to User and not a specific year"""
        registrants=[]
        for c in self.coach.all():
            try:
                registrants.append(Registrant.objects.get(con=self.con, user=c.user))
            except:
                pass
        return registrants

    def skills_allowed(self):
        if self.skill:
            allowed=list(self.skill)
            if "O" in allowed:
                allowed.remove("O")
        else:
            allowed=["A","B","C","D"]
        return allowed

    def skill_display(self):
        """This makes it so I don't see A0, just A, or AB, or something more understandable"""
        prettify=''.join(self.skills_allowed())
        return prettify

    def skill_tooltip_title(self):
        if self.skill:
            allowed=self.skills_allowed()
            allowed.sort(reverse=True)
            skill_dict=dict(SKILL_LEVEL)
            str_base="Registrant must identify skill as"
            str_end= " in Profile in order to register"
            str_mid=""
            for item in allowed:
                if item:
                    displayable=skill_dict.get(item)
                    if item==allowed[-1]:
                        item_str=" or "+displayable
                    else:
                        item_str=" "+displayable+","

                str_mid+=item_str
            return str_base+str_mid+str_end
        else:
            return "No skill restrictions for registration"

    def skill_icon(self):
        if not self.skill:
            return "glyphicon icon-universal-access"

    def intl_icon(self):
        if self.intl:
            #return "glyphicon icon-passportbig"
            #return "glyphicon icon-plane-outline"
            return "glyphicon icon-globe-alt"
        else:
            return "glyphicon icon-universal-access"

    def intl_text(self):
        if self.intl:
            return "International"
        else:
            return None

    def intl_tooltip_title(self):
        if self.intl:
            return "Registrant must qualify as 'International' in order to register. Any MVP can audit and non-INTL auditing skaters MIGHT be allowed to participate as if registered if space is available."
        else:
            return "No location restrictions for registration"

    def onsk8s_icon(self):
        if self.onsk8s:
            return "glyphicon icon-onskates"
        else:
            return "glyphicon icon-shoes"

    def onsk8s_tooltip_title(self):
        if self.onsk8s:
            return "This is an On-Skates Training."
        else:
            return "This is an Off-Skates Training."

    def passes_allowed(self):
        if self.onsk8s:
            allowed=['MVP']
        else:
            allowed=['MVP','Skater','Offskate']

        return allowed

    def passes_tooltip_title(self):
        pass_list=self.passes_allowed()
        pass_string=""
        if len(pass_list)>1:
            if len(pass_list)>2:
                for item in pass_list[:-1]:
                    pass_string+=item+", "
            else:
                pass_string+=pass_list[0]
            pass_string+=" or "+pass_list[-1]
        else:
            pass_string=pass_list[0]

        base_str=self.onsk8s_tooltip_title()

        tooltip_title = base_str+(" Registrant must have %s pass in order to register"%(pass_string))
        return tooltip_title

    def contact_icon(self):
        if self.contact:
            return "glyphicon icon-helmet"
        else:
            return "glyphicon icon-nocontact"

    def contact_text(self):
            return "Contact: "

    def contact_tooltip_title(self):
        if self.contact:
            return "This training includes Contact"
        else:
            return "This training does not include Contact"


    def full_description(self):
        """returns training description, than coach description for each coach. or empty quotes"""
        des=""
        if self.description:
            des+=self.description
        for c in self.coach.all():
            if c.description:
                des+="\n"+c.description
        return des

    def save(self, *args, **kwargs):
        '''custom functions: removes non-ascii chars and punctuation from names, colors'''
        string_fields=['name','description','communication']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                #NOTEE: I'm allowing punctuation in name and description, hope this doesn't bite me
                #usualy I strip all punctuation
                cleaned_att=ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        if self.internal_notes:
            cleaned_notes=ascii_only(self.internal_notes)
            self.internal_notes=cleaned_notes

        if not self.duration:
            if self.onsk8s:
                self.duration=DEFAULT_ONSK8S_DURATION
            else:
                self.duration=DEFAULT_OFFSK8S_DURATION

        super(Training, self).save()

    class Meta:
        ordering=('-con__start','name')

class Coach(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True)
    can_email=models.BooleanField(default=True)

    internal_notes= models.TextField(null=True,blank=True)

    def __unicode__(self):
        try:
            return "Coach %s" % (self.user.first_name)
        except:
            return self.id

    def save(self, *args, **kwargs):
        '''custom functions: removes non-ascii chars'''
        string_fields=['description','internal_notes']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                #NOTEE: I'm allowing punctuation in notes and description, hope this doesn't bite me
                #usualy I strip all punctuation
                cleaned_att=ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        super(Coach, self).save()

    def get_absolute_url(self):#https://docs.djangoproject.com/en/1.7/ref/urlresolvers/#django.core.urlresolvers.reverse
        from scheduler.views import view_coach
        return reverse('scheduler.views.view_coach', args=[str(self.pk)])

    def unconfirmed_trainings(self):
        '''Returns a list of all trainings in which have been submitted,but is not accepted by RC.
        This only matters for coaches, bc you can only register to attend trainigns that have been approved.'''
        from scheduler.models import Training #put here to avoid import error with Matching_Criteria
        unconfirmed=list(self.training_set.filter(RCaccepted=False))#this only returns if coach, since registraiton m2m is attached to roster object.
        return unconfirmed


    class Meta:
        ordering=('user',)
