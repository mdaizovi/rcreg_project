from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.core.urlresolvers import reverse
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from scheduler.app_settings import MAX_CAPTAIN_LIMIT
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME,BPT_Affiliate_ID
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from con_event.signals import update_user_fl_name,delete_homeless_user,clean_registrant_import,match_user,sync_reg_permissions

#from django.db import connection as dbconnection #for checking db hits and speed
#print "dbc0:", len(dbconnection.queries) #syntax reminder, for checking db hits and speed

AMPM=(('AM','AM'),('PM','PM'))

LOCATION_TYPE=(('Flat Track', 'Flat Track'),('Banked Track', 'Banked Track'),('EITHER Flat or Banked Track', 'EITHER Flat or Banked Track'),('Off Skates Athletic Training', 'Off Skates Athletic Training'), ('Seminar/Conference Room', 'Seminar/Conference Room'))
LOCATION_TYPE_FILTER=(('Flat Track', ['Flat Track']),('Banked Track', ['Banked Track']),('EITHER Flat or Banked Track', ['Flat Track','Banked Track']),('Off Skates Athletic Training', ['Off Skates Athletic Training']), ('Seminar/Conference Room', ['Seminar/Conference Room']))
LOCATION_CATEGORY=(("Competition Half Length Only","Competition Half Length Only"),("Competition Any Length","Competition Any Length"),("Training","Training"),("Training or Competition","Training or Competition"),("Classroom","Classroom"))
LOCATION_CATEGORY_FILTER=(("Competition Half Length Only",["Competition Half Length Only"]),("Competition Any Length",["Competition Any Length","Competition Half Length Only","Competition","Training or Competition"]),("Training",["Training","Training or Competition"]),("Training or Competition",["Training or Competition","Training","Competition","Competition Half Length Only","Competition Any Length"]),("Classroom",["Classroom"]))

GENDER= (('Female', 'Female'), ('Male', 'Male'), ('NA/Coed','NA/Coed'))
SKILL_LEVEL_SK8R= ((None,'NA'),('D', 'Rookie'), ('C', 'Beginner'),('B', 'Intermediate'), ('A', 'Advanced'))
SKILL_LEVEL_ACT= ((None, "No skill restrictions; all levels welcome"),('ABC', 'All Contact Safe (A-C)'),('CO', 'Beginner Only- no Coed (C)'),('BC', 'Beginner/Intermediate Only (B-C)'),('BO', 'Intermediate Only (B)'),('AB', 'Intermediate / Advanced Only (A-B)'),('AO', 'Advanced Only (A)'))
SKILL_LEVEL_TNG = tuple(list(SKILL_LEVEL_ACT[:2]) + [tuple(SKILL_LEVEL_ACT[-2])])#this weirdnes is neseccary, don't touch it
SKILL_LEVEL_CHG = tuple([tuple(SKILL_LEVEL_ACT[0])]+list(SKILL_LEVEL_ACT[2:]))
SKILL_LEVEL_GAME = SKILL_LEVEL_CHG #I'm not whether i want this the same or not, but now i need ot keep so no import error
SKILL_LEVEL= SKILL_LEVEL_SK8R+SKILL_LEVEL_ACT
PASS_TYPES=(('MVP', 'MVP'), ('Skater', 'Skater'), ('Offskate', 'Offskate'))

#reminder: mvp can do everything, skater can do challenges and off skates trainings but no on skates trainings, and offskate is self explanatiory

class Country(models.Model):
    name=models.CharField(max_length=50, primary_key=True)
    slugname=models.CharField(max_length=3,unique=True)

    def __unicode__(self):
       return "%s (%s)" % (self.name, self.slugname)

    class Meta:
        ordering=['name']

class State(models.Model):
    slugname=models.CharField(max_length=4,primary_key=True)
    name=models.CharField(max_length=50, unique=True)
    country = models.ForeignKey(Country,null=True, blank=True, on_delete=models.SET_NULL)

    def __unicode__(self):
       return "%s (%s)" % (self.name, self.slugname)

    class Meta:
        ordering=['name']

class ConManager(models.Manager):

    def upcoming_cons(self):
        '''Gets list of Cons that are coming soonest without having ended more than 7 days ago.
        I chose 7 arbitrarily, assuming no one will be adding stuff more than a week after a Con,
        but wanting to leave room to potentially prepare for more than 1 Con per year.
        Will always return a list, even if an empty one.'''
        cutoff=datetime.date.today() - datetime.timedelta(days=7)
        upcoming=list(Con.objects.filter(end__gte=datetime.date(cutoff.year, cutoff.month, cutoff.day)).order_by('start'))
        return upcoming

    def past_cons(self):
        '''Gets list of cons whose end date is more than 1 week from today'''
        cutoff=datetime.date.today() + datetime.timedelta(days=7)
        past=list(Con.objects.filter(end__lte=datetime.date(cutoff.year, cutoff.month, cutoff.day)).order_by('-start'))
        return past

    def most_upcoming(self):
       '''Gets single most upcoming Con, without having ended more than 7 days ago. Dependont on/see upcoming_cons above
       If no upcoming Cons, returns None'''
       upcoming=self.upcoming_cons()
       try:
           most_upcoming_con=upcoming[0]
       except:
           most_upcoming_con=Con.objects.latest('start')

       return most_upcoming_con

    def most_recent(self):
       '''Gets single most recent past Con, having ended more than 7 days ago. Dependont on/see past_cons above
       If no past Cons, returns None'''

       past=self.past_cons()
       try:
           most_recent_con=past[0]
           return most_recent_con
       except:
           return None

class Con(models.Model):
    city = models.CharField(max_length=100,default="Las Vegas")
    state=models.ForeignKey(State,null=True, blank=True, on_delete=models.SET_NULL)#https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.ForeignKey.on_delete
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    start = models.DateField(auto_now=False, auto_now_add=False)
    venue=models.ManyToManyField("scheduler.Venue", blank=True)
    end = models.DateField(auto_now=False, auto_now_add=False)
    year = models.IntegerField()

    challenge_submission_start=models.DateField(auto_now=False, auto_now_add=False,null=True, blank=True)
    training_submission_end=models.DateField(auto_now=False, auto_now_add=False,null=True, blank=True)
    sched_visible=models.BooleanField(default=False)
    sched_final=models.BooleanField(default=False)

    hoursb4signup=models.FloatField(default=2.0)
    morning_class_cutoff=models.TimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    dayb4signup_start=models.TimeField(auto_now=False, auto_now_add=False,null=True, blank=True)

    BPT_event_id=models.CharField(max_length=100,null=True, blank=True)
    ticket_link=models.URLField(null=True, blank=True)
    hotel_book_link=models.URLField(null=True, blank=True)
    objects = ConManager()

    def __unicode__(self):
       return "%s %s" % (self.year, self.city)

    class Meta:
        ordering=('-start',)
        unique_together = ('city', 'year')

    def get_event_link(self):
        if self.BPT_event_id:
            BPT_General_link='http://www.brownpapertickets.com/'
            link=BPT_General_link+'ref/'+BPT_Affiliate_ID+'/event/'+self.BPT_event_id
            return link
        else:
            return None

    def schedule_final(self):
        #This method was written before the field was created.
        #I should find everywhere I put this and just replace it. I don't know where all it is, don't care enough to make a mess by missing a few
        if self.sched_final:
            return True
        else:
            return False

    def get_unscheduled_acts(self):
        """Gathers unscheduled Challenges and Trainings so they can be culled after the schedule is final."""
        c_no_os=[]
        t_no_os=[]
        if self.sched_final:
            from scheduler.models import Challenge, Training# here insted of top to preventimport error
            dead_chals=Challenge.objects.filter(con=self)
            for c in dead_chals:
                if c.occurrence_set.all().count()<1:
                    c_no_os.append(c)

            dead_trains=Training.objects.filter(con=self)
            for t in dead_trains:
                if t.occurrence_set.all().count()<1:
                    t_no_os.append(t)

        return c_no_os,t_no_os



    def can_submit_chlg_by_date(self):
        """"only checks to see if there is a challenge submission date and that date has passed.
        Does not check if received too many submissions already"""
        can_submit=False
        if self.challenge_submission_start:
            if self.challenge_submission_start<=datetime.date.today():
                can_submit=True
        return can_submit

    def can_submit_chlg(self):
        """Checks both is submisison date has passed and if submission isn't clused due to too many submissions"""
        from scheduler.models import Challenge
        can_submit=self.can_submit_chlg_by_date()

        if can_submit:
            submission_full=Challenge.objects.submission_full(self)
            if submission_full:
                can_submit=False

        return can_submit

    def can_submit_trng_by_date(self):
        """"only checks to see if there is a training submission end date and that date has passed.
        Does not check if received too many trainings already (currently no such thing as too many trainings)"""
        can_submit=False
        if self.training_submission_end:
            if self.training_submission_end >= datetime.date.today():
                can_submit=True
        return can_submit

    def get_date_range(self):
        date_list=[]
        if self.start and self.end:
            day = self.start
            delta = datetime.timedelta(days=1)
            stop=self.end+delta
            while day < stop:
                date_list.append(day)
                day += delta

        return date_list

    def get_locations(self):
        """Gets all locations assosciated w/ Con. Used a lot in Calendr/scheduling"""
        from scheduler.models import Location
        venues=self.venue.all()
        locations=[]
        for v in venues:
            for l in v.location_set.all():
                if l not in locations:
                    locations.append(l)
        return locations

    def save(self, *args, **kwargs):

        if self.year != self.start.year:
            self.year = self.start.year

        if self.start:#split up because I always mess up conditionals w/ too many conditions
            if not self.challenge_submission_start or not self.training_submission_end:
                month=self.start.month-4
                #If Con is at end of July, this will make chal submission start 3/1 and training submisison end 5/15
                if not self.challenge_submission_start:
                    dt=datetime.date(self.start.year, month, 1)
                    self.challenge_submission_start=dt
                if not self.training_submission_end:
                    dt2=datetime.date(self.start.year, month+2, 15)
                    self.training_submission_end=dt2

        if not self.morning_class_cutoff:
            self.morning_class_cutoff=datetime.time(hour=9,minute=30)

        if not self.dayb4signup_start:
            self.dayb4signup_start=datetime.time(hour=21,minute=30)

        if not self.country:
            self.country=Country.objects.get(name="United States")
            self.state=State.objects.get(name="Nevada")

        if not self.hotel_book_link:
            self.hotel_book_link="http://rollercon.com/register/hotel-reservations/"
        if not self.ticket_link:
            self.ticket_link="http://rollercon.com/register/rollercon-pass/"

        super(Con, self).save()


class Blackout(models.Model):
    registrant=models.ForeignKey('Registrant',related_name="blackout")#did not set null on delete, I'm okay with this going away if registrant goes away
    date=models.DateField()
    ampm=models.CharField(max_length=100, choices=AMPM)

    def __unicode__(self):
        return "%s %s (%s)" % (self.registrant, self.date,self.ampm)

    def make_temp_o(self):
        """takes a temporary, unsaved occurrence from blackout, for use in auto scheduling to indicate person busy at this time"""
        from swingtime.models import Occurrence
        if self.ampm=="AM":
            start_time=datetime.datetime(self.date.year, self.date.month, self.date.day, 0, 30)
            end_time=datetime.datetime(self.date.year, self.date.month, self.date.day, 11, 29)
        elif self.ampm=="PM":
            start_time=datetime.datetime(self.date.year, self.date.month, self.date.day, 12, 30)
            end_time=datetime.datetime(self.date.year, self.date.month, self.date.day, 23, 29)
        tempo=Occurrence(start_time=start_time,end_time=end_time)

        return tempo


    class Meta:
        ordering=('registrant','date')
        unique_together = ('registrant','date','ampm')

class Matching_Criteria(models.Model):
    """"used to match registrants to activities"""
    con = models.ForeignKey(Con,null=True,blank=True,on_delete=models.SET_NULL)
    skill=models.CharField(max_length=30, null=True,blank=True,choices=SKILL_LEVEL)
    gender=models.CharField(max_length=30, choices=GENDER, default=GENDER[0][0])
    intl=models.NullBooleanField(default=False)

    # def coed_beginner(self):
    #     #maybe write something simialr for minimum contact skills?
    #     if self.gender=='NA/Coed':
    #         forbidden_skills=[None,False,'C','CO','BC','ABC','BO']
    #         if self.skill in forbidden_skills:
    #             self.skill="BO"
    #             self.save()
    #             return "Coed teams have a minimum skill level of Intermediate. In order to remain coed, the skill level has been raised to Intermediate. If you'd like to include a lower skill level, please change team gender first."
    #     else:
    #         return False

    def skills_allowed(self):
        #this is only necessary for rosters, not registrants, but moved it here anyway.
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

    def gender_icon(self):
        if self.gender==GENDER[0][0]:#If Female
            return "fa fa-venus"
        elif self.gender==GENDER[1][0]:#if male
            return "fa fa-mars"
        elif self.gender==GENDER[2][0]:#if na/coed
            return "fa fa-venus-mars"
            #return "glyphicon icon-universal-access"

    def gender_text(self):
        if self.gender==GENDER[0][0]:#If Female
            return "Female"
        elif self.gender==GENDER[1][0]:#if male
            return "Male"
        elif self.gender==GENDER[2][0]:#if na/coed
            return "NA/Coed"

    def gender_tooltip_title(self):
        if self.gender==GENDER[0][0]:#If Female
            return "Registrant must identify as 'Female' in Profile in order to register"
        elif self.gender==GENDER[1][0]:#if male
            return "Registrant must identify as 'Male' in Profile in order to register"
        elif self.gender==GENDER[2][0]:#if na/coed
            return "No gender restrictions for registration"

    def save(self, *args, **kwargs):
        if not self.intl:
            self.intl=False #I don't like None, I just leave it for default select widget

        super(Matching_Criteria, self).save()

    class Meta:
        abstract = True

class RegistrantManager(models.Manager):

    def eligible_sk8ers(self, roster):
        '''roster relates to training or challenge roster, this returns list of eligible registrants
        only checks gender, intll, skill and con.'''
        already_registered=list(roster.participants.all())#this works regardless of Roster or TrainingRoster
        from scheduler.models import Challenge
        #this challenge doesn't matter if is training, will just turn up empty
        if hasattr(roster, 'captain'):
            #makes sure people on opposing team can't be selected.
            challenge_set=list(Challenge.objects.filter(Q(roster1=roster)|Q(roster2=roster)))
            opposing_skaters=[]
            for c in challenge_set:
                for r in [c.roster1, c.roster2]:
                    if r and r != roster and r.participants:
                        for skater in r.participants.all():
                            opposing_skaters.append(skater)
            already_registered+=opposing_skaters

        if hasattr(roster, 'captain'):#if is Roster
            eligibles=Registrant.objects.filter(pass_type__in=roster.passes_allowed(),con=roster.con, gender__in=roster.genders_allowed(),intl__in=roster.intls_allowed(),skill__in=roster.skills_allowed()).exclude(id__in=[o.id for o in already_registered])
        else:#if is TrainingRoster:
            if roster.registered:
                training=roster.registered.training
                eligibles=Registrant.objects.filter(pass_type__in=training.passes_allowed(),con=training.con,intl__in=roster.intls_allowed(),skill__in=training.skills_allowed()).exclude(id__in=[o.id for o in already_registered])
            elif roster.auditing:
                training=roster.auditing.training
                eligibles=Registrant.objects.filter(con=training.con).exclude(id__in=[o.id for o in already_registered])
        return eligibles

class Registrant(Matching_Criteria):

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    pass_type=models.CharField(max_length=30, choices=PASS_TYPES, default='MVP')
    #the only 3 necessary and unique fields, besides con, which is in matching criteria
    email=models.EmailField(max_length=50)
    #remember, email can't be unique=true across the board bc same email for same person for different cons.
    #but it is unique for email and con.

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    sk8name = models.CharField(max_length=30,null=True, blank=True)
    sk8number = models.CharField(max_length=30,null=True, blank=True)

    country = models.ForeignKey(Country,null=True, blank=True, on_delete=models.SET_NULL)
    state=models.ForeignKey(State,null=True, blank=True, on_delete=models.SET_NULL)
    objects = RegistrantManager()
    captaining=models.IntegerField(null=True, blank=True)

    #I don't care about this data, but maybe keeping it will be helpful?
    BPT_Ticket_ID=models.CharField(max_length=30,null=True, blank=True)
    affiliation=models.CharField(max_length=100, null=True,blank=True)
    ins_carrier=models.CharField(max_length=100, null=True,blank=True)
    ins_number=models.CharField(max_length=100, null=True,blank=True)
    age_group=models.CharField(max_length=100, null=True,blank=True)
    favorite_part=models.CharField(max_length=100, null=True,blank=True)
    volunteer=models.CharField(max_length=100, null=True,blank=True)

    internal_notes= models.TextField(null=True,blank=True)

    @property
    def name(self):
        if self.sk8name and self.sk8number:
            return "%s %s" % (self.sk8name, self.sk8number)
        elif self.sk8name:
            return "%s" % (self.sk8name)
        elif self.first_name and self.last_name:
            return "%s %s" % (self.first_name, self.last_name)
        else:
            return "Incomplete Name record"

    @property
    def realname(self):
        if self.first_name and self.last_name:
            return "%s %s" % (self.first_name, self.last_name)
        else:
            return "Incomplete Name Record"


    def __unicode__(self):
        return self.name+": "+str(self.con)

    def is_intl(self,con):
        '''Returns True if  is considered INTL for supplied Con. Else, False'''
        if self.country and (self.country == con.country):
            if self.state:
                if self.state != con.state and self.state.slugname in ["HI","AK","AP"]:
                    return True
            else:
                return False
        elif not self.country:
            return False
        else:
            return True

    def can_sk8(self):
        #if self.pass_type=='MVP' or self.pass_type=='Skater':#why did I write it this way?
        if self.pass_type in ['MVP','Skater']:
            return True
        else:
            return False

    def is_a_captain(self):
        from scheduler.models import Challenge #put here to avoid import error with Matching_Criteria
        my_challenges=Challenge.objects.filter(Q(roster1__captain=self)|Q(roster2__captain=self))
        if len(my_challenges)>0:
            return my_challenges
        else:
            return False

    def can_captain(self):
        from scheduler.models import Challenge #put here to avoid import error with Matching_Criteria
        my_challenges=list(Challenge.objects.filter(is_a_game=False).filter(Q(roster1__captain=self)|Q(roster2__captain=self)))
        if self.can_sk8() and len(my_challenges) < MAX_CAPTAIN_LIMIT:
            return True
        else:
            return False

    def criteria_conflict(self):
        problem_criteria=[]
        potential_conflicts=[]
        captain_conflict=False
        for roster in list(self.roster_set.all()):
            if self.gender not in roster.genders_allowed():
                if "gender" not in problem_criteria:
                    problem_criteria.append("gender")
                if roster not in potential_conflicts:
                    potential_conflicts.append(roster)
                if roster.captain and roster.captain==self:
                    captain_conflict=True
            if self.skill not in roster.skills_allowed():
                if "skill" not in problem_criteria:
                    problem_criteria.append("skill")
                if roster not in potential_conflicts:
                    potential_conflicts.append(roster)
                if roster.captain and roster.captain==self:
                    captain_conflict=True

        if len(potential_conflicts)>0:
            return problem_criteria,potential_conflicts,captain_conflict
        else:
            return None,None,captain_conflict

    def conflict_sweep(self):
        '''Calls criteria_conflict, removes from any rosters that have conflicts,
        Doesn't let you do it if are captain.
        ONLY WRITTEN FOR CHALLENGE, NOT TRAINING.'''
        problem_criteria,potential_conflicts,captain_conflict=self.criteria_conflict()
        if not captain_conflict:
            if potential_conflicts:
                for roster in potential_conflicts:
                    roster.participants.remove(self)
                    roster.save()
            return True
        else:
            return False


    def update_blackouts(self,bo_tup_list):
        """Takes in a dictionary w/ date object as key, list w/ ["AM","PM"], or 1, as value.
        These are all of the blackouts that *should* exist. Takes dict and creates and deletes as appropriate."""
        existing_bo_tup_list=[]
        for bo in self.blackout.all():
            existing_bo_tup_list.append((bo.date,bo.ampm))

        #make new ones
        for tup in bo_tup_list:
            if tup not in existing_bo_tup_list:
                date=tup[0]
                ampmitem=tup[1]
                Blackout.objects.get_or_create(registrant=self,ampm=ampmitem,date=date)

        #delete old ones
        for tup in existing_bo_tup_list:
            if tup not in bo_tup_list:
                date=tup[0]
                ampmitem=tup[1]
                try:
                    Blackout.objects.get(registrant=self,date=date,ampm=ampmitem).delete()
                except:
                    print "error deleting blackout: ",self, date, ampmitem

    def get_occurrences(self):
        """gets all occurrences registrant is on roster for. """
        from swingtime.models import Occurrence, TrainingRoster #need here in case of import error?
        reg_coach=self.user.is_a_coach()
        reg_os=[]

        if reg_coach:
            coach_trains=reg_coach.training_set.filter(con=self.con).prefetch_related('occurrence_set')
            for t in coach_trains:
                reg_os+=list(t.occurrence_set.all())

        reg_ros=list(self.roster_set.all())
        chal=[]
        for ros in reg_ros:
            chal+=list(ros.roster1.all())
            chal+=list(ros.roster2.all())

            for c in chal:
                for o in c.occurrence_set.all(): #othersise it gets added 2x
                    if o not in reg_os:
                        reg_os.append(o)
        reg_os.sort(key=lambda o: o.start_time)

        return reg_os

    def is_occupied(self,pending_o):
        """Takes in pending occurrence, checks to see if it conflicts w/ anything skater is doing at moment"""
        from swingtime.models import Occurrence #need here in case of import error?
        from scheduler.models import Challenge, Training,Coach
        sk8er_ros=self.roster_set.all()
        sk8er_chal=list(Challenge.objects.filter(RCaccepted=True).filter(Q(roster1__in=sk8er_ros)|Q(roster2__in=sk8er_ros)))

        if hasattr(self.user, 'coach'):
            sk8er_train=self.user.coach.training_set.filter(con=self.con)
        else:
            sk8er_train=[]

        concurrent=list(Occurrence.objects.filter(start_time__lt=(pending_o.end_time + datetime.timedelta(minutes=30)),end_time__gt=(pending_o.start_time - datetime.timedelta(minutes=30))).filter(Q(challenge__in=sk8er_chal)|Q(training__in=sk8er_train)).exclude(pk=pending_o.pk))

        if len(concurrent)>0:
            return concurrent
        else:
            return False

    def is_occupied_coaching(self,pending_o):
        """Same as is_occupied, but only cares if they are coaching at that moment. Challenges aren't looked for."""
        from swingtime.models import Occurrence #need here in case of import error?
        from scheduler.models import Challenge, Training,Coach
        sk8er_ros=self.roster_set.all()
        sk8er_chal=list(Challenge.objects.filter(RCaccepted=True).filter(Q(roster1__in=sk8er_ros)|Q(roster2__in=sk8er_ros)))

        if hasattr(self.user, 'coach'):
            sk8er_train=self.user.coach.training_set.filter(con=self.con)

            concurrent=list(Occurrence.objects.filter(training__in=sk8er_train).filter(start_time__lt=(pending_o.end_time + datetime.timedelta(minutes=30)),end_time__gt=(pending_o.start_time - datetime.timedelta(minutes=30))).exclude(pk=pending_o.pk))

            if len(concurrent)>0:
                return concurrent
            else:
                return False
        else:
            return False


    def check_conflicts(self):
        """Gets occurrences, checks to see if any are at conflicting times """
        from swingtime.models import Occurrence #need here in case of import error?
        from scheduler.models import Challenge, Training,Coach
        reg_os=self.get_occurrences()
        conflict=[]
        free=[]

        sk8er_ros=self.roster_set.all()
        sk8er_chal=list(Challenge.objects.filter(RCaccepted=True).filter(Q(roster1__in=sk8er_ros)|Q(roster2__in=sk8er_ros)))

        if hasattr(self.user, 'coach'):
            sk8er_train=self.user.coach.training_set.filter(con=self.con)
        else:
            sk8er_train=[]

        for o in reg_os:
            concurrent=Occurrence.objects.filter(start_time__lt=(o.end_time + datetime.timedelta(minutes=30)),end_time__gt=(o.start_time - datetime.timedelta(minutes=30))).filter(Q(challenge__in=sk8er_chal)|Q(training__in=sk8er_train)).exclude(pk=o.pk)

            if len(concurrent)<1:
                free.append(o)
            else:
                if o not in conflict:
                    conflict.append(o)

        return conflict,free


    def get_trainings_attended(self):
        """Gets Trainings was on registered or auditing rosters for"""
        from swingtime.models import Occurrence, TrainingRoster #need here in case of import error?

        trainingrosters=self.trainingroster_set.all() #do select/prefetch related later
        trainings=[]
        for tr in trainingrosters:
            if tr.registered:
                o=tr.registered
            elif tr.auditing:
                o=tr.auditing
            else:
                o=None #should never happen
            if o and o.training:
                trainings.append(o.training)

        return trainings


    def get_my_schedule_url(self):
        """Used for bosses to check someone's schedule
        at point of writing I dont know where to link ot this, just thought I might as well add it"""
        from scheduler.views import my_schedule
        url = "%s?registrant=%s" % (reverse('scheduler.views.my_schedule'),self.pk)
        return url

    def save(self, *args, **kwargs):

        string_fields=['first_name','last_name','sk8name','sk8number','BPT_Ticket_ID','affiliation','ins_carrier','ins_number','age_group','favorite_part','volunteer']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                cleaned_att=ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)

        if self.internal_notes:
            cleaned_notes=ascii_only(self.internal_notes)
            self.internal_notes=cleaned_notes

        if not self.sk8number:
            self.sk8number="X"

        if not self.con:
            upcoming=Con.objects.most_upcoming()
            self.con=upcoming

        if self.is_a_captain():
            self.captaining=len(self.is_a_captain().exclude(is_a_game=True))
        else:
            self.captaining=0

        if not self.intl:#if you manually make them intl, fine, it'll stay.
            self.intl=self.is_intl(self.con)
        super(Registrant, self).save()

    class Meta:
        ordering=('con','sk8name','last_name','first_name')
        unique_together = (('con','email'),('con','user'),('con','last_name','first_name','sk8name'))

pre_save.connect(clean_registrant_import, sender=Registrant)
#shouldn't match_user be a pre-save?
post_save.connect(match_user, sender=Registrant)

post_save.connect(update_user_fl_name, sender=Registrant)
post_save.connect(sync_reg_permissions, sender=Registrant)
pre_delete.connect(delete_homeless_user, sender=Registrant)

class Blog(models.Model):
    headline = models.CharField(max_length=200,unique=True)
    slugname=models.CharField(max_length=100,null=True, blank=True)
    date=models.DateField(default=timezone.now)
    user=models.ForeignKey(User,limit_choices_to={'is_staff': True},null=True, blank=True, on_delete=models.SET_NULL)
    post= models.TextField()

    def __unicode__(self):
        return "%s (%s)" % (self.headline, self.date)

    class Meta:
        ordering=('-date',)

    def getslugname(self):
        if not self.slugname or self.slugname=="":
            self.slugname=self.headline.replace(' ', '_')
        return self.slugname

    def get_next_and_previous(self):

        try:
            next_blog=self.get_next_by_date()
        except:
            next_blog=None
        try:
            previous_blog=self.get_previous_by_date()
        except:
            previous_blog=None
        return next_blog,previous_blog

    def save(self, *args, **kwargs):
        string_fields=['headline']
        for item in string_fields:
            att_unclean=getattr(self, item)
            if att_unclean:
                cleaned_att=ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)
        cleaned_post=ascii_only(self.post)
        self.post=cleaned_post

        if not self.slugname:
            self.getslugname()

        super(Blog, self).save()

    def get_absolute_url(self):
        from con_event.views import announcement
        return reverse('con_event.views.announcement', args=[str(self.slugname)])
