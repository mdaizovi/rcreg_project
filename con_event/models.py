#con_event.models
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from django.core.urlresolvers import reverse#for absolute url #https://docs.djangoproject.com/en/1.8/ref/urlresolvers/#django.core.urlresolvers.reverse
#from datetime import datetime, timedelta
#from . import signals #this file exists but it's blank bc I decided to put the signals under the models
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
from scheduler.app_settings import MAX_CAPTAIN_LIMIT
from django.db import connection as dbconnection
from django.forms.models import model_to_dict
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME,BPT_Affiliate_ID
from django.db.models.signals import pre_save, post_save,post_delete,pre_delete,post_init,pre_init
from con_event.signals import update_user_fl_name,delete_homeless_user,clean_registrant_import,match_user,sync_reg_permissions
import logging
#Get an instance of a logger
logger = logging.getLogger(__name__)

AMPM=(('AM','AM'),('PM','PM'))
LOCATION_TYPE=(('Flat Track', 'Flat Track'),('Banked Track', 'Banked Track'),('EITHER Flat or Banked Track', 'EITHER Flat or Banked Track'), ('Any Skateable Surface', 'Any Skateable Surface'), ('Seminar/Conference Room', 'Seminar/Conference Room'),('Other', 'Other'))
GENDER= (('Female', 'Female'), ('Male', 'Male'), ('NA/Coed','NA/Coed'))
SKILL_LEVEL_SK8R= ((None,'NA'),('D', 'Rookie'), ('C', 'Beginner'),('B', 'Intermediate'), ('A', 'Advanced'))
SKILL_LEVEL_ACT= ((None, "No skill restrictions; all levels welcome"),('ABC', 'All Contact Safe (A-C)'),('CO', 'Beginner Only- no Coed (C)'),('BC', 'Beginner/Intermediate Only (B-C)'),('BO', 'Intermediate Only (B)'),('AB', 'Intermediate / Advanced Only (A-B)'),('AO', 'Advanced Only (A)'))
SKILL_LEVEL_TNG = tuple(list(SKILL_LEVEL_ACT[:2]) + [tuple(SKILL_LEVEL_ACT[-2])])#this weirdnes is neseccary, don't touch it
SKILL_LEVEL_CHG = tuple([tuple(SKILL_LEVEL_ACT[0])]+list(SKILL_LEVEL_ACT[2:]))
SKILL_LEVEL= SKILL_LEVEL_SK8R+SKILL_LEVEL_ACT
#INSURANCE= (('W', 'WFTDA'), ('U', 'USARS'), ('C','CRDi'),('EPA','Event Pass ALREADY purchased'),('EPW','Event Pass WILL be purchased'))
PASS_TYPES=(('MVP', 'MVP'), ('Skater', 'Skater'), ('Offskate', 'Offskate'))

#reminder: mvp can do everything, skater can do challenges and off skates trainings but no on skates trainings, and offskate is self explanatiory

#AGE_GROUP= (('<18', '<18'),('19-20', '19-20'),('21-30', '21-30'), ('31-40', '31-40'), ('41-50','41-50'),('50+','50+'),('NA','Not yr bizness'))
#FAV_PART= (('1st', 'This is my first Rollercon!'),('ONSK8', 'On Skates Training'),('OFFSK8', 'Off Skates Training'), ('BCP', 'Bouts & Challenges (playing)'), ('BCW', 'Bouts & Challenges (watching)'),('SW','Seminars & Workshops'),('247P','24/7 Pool Party'),('BNB','Black n Blue & PM Social Events'),('OSS','Open Skate & Scrimmages'),('VN','Volunteering'),('VV','Vendor Village'))
#INSURANCE= (('W', 'WFTDA'), ('U', 'USARS'), ('C','CRDi'),('EPA','Event Pass ALREADY purchased'),('EPW','Event Pass WILL be purchased'))
#RULESET=(('W', 'WFTDA'), ('U', 'USARS'),('M', 'MRDA'), ('J', 'JRDA'), ('R', 'RDCL'),('O', 'OTHER'))
#YEARS_PLAYING= (('1', '<2'),('2', '2-4'),('5', '5-7'), ('8', '8 or more'),('NA', "Supporter/fan, not a player" ),('NYB','Not yr bizness'))
#Bool_Choices= (('Y', 'Yes'), ('N', 'No'))

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
        I chose 7 arbitrarily, assuming no one will be adding s more than a week after a Con,
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
       ######should I consolidate most_upcoming with most_recent, or will that get confusing? or it it better to DRY it up?
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
    end = models.DateField(auto_now=False, auto_now_add=False)
    challenge_submission_start=models.DateField(auto_now=False, auto_now_add=False,null=True, blank=True)
    training_submission_end=models.DateField(auto_now=False, auto_now_add=False,null=True, blank=True)
    year = models.IntegerField()
    BPT_event_id=models.CharField(max_length=100,null=True, blank=True)
    objects = ConManager()
    ticket_link=models.URLField(null=True, blank=True)
    hotel_book_link=models.URLField(null=True, blank=True)

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
        #hard coded badly for now, fix later
        if self.start>=datetime.date.today():
            return False
        else:
            return True

    def can_submit_chlg_by_date(self):
        """"only checks to see if there is a chalenge submission date and that date has passed.
        Does not check if received too many submissions already"""
        can_submit=False
        if self.challenge_submission_start:
            if self.challenge_submission_start<=datetime.date.today():
                can_submit=True
        return can_submit

    def can_submit_chlg(self):
        """Checks both is submisison date has passed and if submission isn't clused due to too many submisisons"""
        from scheduler.models import Challenge
        can_submit=self.can_submit_chlg_by_date()

        if can_submit:
            submission_full=Challenge.objects.submission_full(self)
            if submission_full:
                can_submit=False

        return can_submit

    def can_submit_trng_by_date(self):
        """"only checks to see if there is a training submission end date and that date has passed.
        Does not check if received too many trainings already"""
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

    def save(self, *args, **kwargs):
        '''saves self.year as start.year, if no year already saved'''
        #if not self.year or self.year!=self.start.year:
        if self.year != self.start.year:
            self.year = self.start.year

        if self.start:#split up because I always mess up conditionals w/ too many conditions
            if not self.challenge_submission_start or not self.training_submission_end:
                month=self.start.month-4
                if not self.challenge_submission_start:
                    dt=datetime.date(self.start.year, month, 1)
                    self.challenge_submission_start=dt
                if not self.training_submission_end:
                    dt2=datetime.date(self.start.year, month, 15)
                    self.training_submission_end=dt2

        if not self.country:
            self.country=Country.objects.get(name="United States")
            self.state=State.objects.get(name="Nevada")

        if not self.hotel_book_link:
            self.hotel_book_link="http://rollercon.com/register/hotel-reservations/"
        if not self.ticket_link:
            self.ticket_link="http://rollercon.com/register/rollercon-pass/"


        super(Con, self).save()

class Blackout(models.Model):
    registrant=models.ForeignKey('Registrant',related_name="blackout")
    date=models.DateField()
    ampm=models.CharField(max_length=100, choices=AMPM)

    def __unicode__(self):
        return "%s %s (%s)" % (self.registrant, self.date,self.ampm)

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
        already_registered=list(roster.participants.all())
        from scheduler.models import Challenge
        #this challenge doesn't matter if is training, will just turn up empty
        challenge_set=list(Challenge.objects.filter(Q(roster1=roster)|Q(roster2=roster)))
        opposing_skaters=[]
        for c in challenge_set:
            for r in [c.roster1, c.roster2]:
                if r and r != roster and r.participants:
                    for skater in r.participants.all():
                        opposing_skaters.append(skater)
        already_registered+=opposing_skaters
        eligibles=Registrant.objects.filter(pass_type__in=roster.passes_allowed(),con=roster.con, gender__in=roster.genders_allowed(),intl__in=roster.intls_allowed(),skill__in=roster.skills_allowed()).exclude(id__in=[o.id for o in already_registered])
        return eligibles

class Registrant(Matching_Criteria):

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    pass_type=models.CharField(max_length=30, choices=PASS_TYPES, default='MVP')
    #the only 3 necessary and unique fields, besides con, which is in matching criteria
    email=models.EmailField(max_length=50)
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


    def __unicode__(self):
       return "%s %s %s" % (self.sk8name, self.sk8number, self.con)

    def is_intl(self,con):
        '''Returns True if  is considered INTL for supplied Con. Else, False'''
        if self.country and (self.country == con.country):
            if self.state:
                if self.state != con.state and self.state.slugname in ["HI","AK","AP"]:#mke sure this works
                    return True
            else:
                return False
        elif not self.country:
            return False
        else:
            return True

    def can_sk8(self):
        if self.pass_type=='MVP' or self.pass_type=='Skater':
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

    def unaccepted_challenges(self):
        """returns list of challenges in which registrant is listed as captain but has not accepted challenge,
        or in which registrant is captain, has accepted challenge, but opponent has rejected.
        either way action is require on registrant's part (either accept of find a new opponent)"""
        from scheduler.models import Challenge
        #print "unaccepted challenges",unaccepted_challenges
        unaccepted_challenges=Challenge.objects.filter(Q(roster1__captain=self)|Q(roster2__captain=self)).filter(Q(captain1accepted=False)|Q(captain2accepted=False))
        return unaccepted_challenges

    def unsubmitted_challenges(self):
        '''Returns a list of all chellenges in which Registrant is captain, but challeng has not been submitted
        only if submission day has passed
        don't change this without consulting notify something something in rcreg_project/custom processors.'''
        from scheduler.models import Challenge #put here to avoid import error with Matching_Criteria
        my_rosters=list(Roster.objects.filter(captain=self))
        unsubmitted=Challenge.objects.filter(Q(roster1__in=my_rosters)|Q(roster2__in=my_rosters)).filter(submitted_on=None)
        #print "my unsubmitted",unsubmitted
        return unsubmitted

    def pending_challenges(self):
        '''Returns a list of all chellenges in which Registrant is on roster, but challeng has not been submitted'''
        #####AH! people weren't getting notified of challenges they were invited to, becuse weren't on the roster yet. What a dummy!!!
        from scheduler.models import Challenge,Roster #put here to avoid import error with Matching_Criteria
        my_rosters=list(self.roster_set.all())
        my_cap_rosters=list(Roster.objects.filter(captain=self))
        for r in my_cap_rosters:
            if r not in my_rosters:
                my_rosters.append(r)
        pending=list(Challenge.objects.filter(Q(roster1__in=my_rosters)|Q(roster2__in=my_rosters)).filter(submitted_on=None))
        return pending

    def scheduled_challenges(self):
        '''Returns a list of all chellenges in which Registrant is on roster, and challenge is confirmed'''
        #not written yet, currently no such thing as a scheduled challenge
        return None

    def unconfirmed_challenges(self):
        '''Returns a list of all chellenges in which Registrant is on a roster,
        chalenge has been submitted, but is not accepted by RC. This is wheter or not reg is a captain, captian is irrelevant'''
        from scheduler.models import Challenge #put here to avoid import error with Matching_Criteria
        my_rosters=list(self.roster_set.all())
        unconfirmed=list(Challenge.objects.filter(RCaccepted=False).filter(Q(roster1__in=my_rosters)|Q(roster2__in=my_rosters)).exclude(submitted_on=None))
        return unconfirmed

    def scheduled_trainings(self):
        '''Returns a list of all trainings in which Registrant is on roster'''
        #not written yet, currently no such thing as a scheduled training
        return None

    def unconfirmed_trainings(self):
        '''Returns a list of all trainings in which have been submitted,but is not accepted by RC.
        matched by self.user to coach.user
        This only matters for coaches, bc you can only register to attend trainigns that have been approved.'''
        from scheduler.models import Training,Coach #put here to avoid import error with Matching_Criteria
        try:
            coach_me=Coach.objects.get(user=user)
        except:
            coach_me=None
        if coach_me:
            unconfirmed=list(coach_me.training_set.filter(RCaccepted=False, con=self.con))#this only returns if coach, since registraiton m2m is attached to roster object.
            return unconfirmed
        else:
            return None

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
        '''calls criteria_conflict, removes from any rosters that have conflicts,
        including removing self as captain, making challenges unconfirmed
        ONLY WRITTEN FOR CHALLENGE, NOT TRAINING, DO LATER'''
        problem_criteria,potential_conflicts,captain_conflict=self.criteria_conflict()
        if not captain_conflict:
            if potential_conflicts:
                for roster in potential_conflicts:
                    roster.participants.remove(self)
                    roster.save()
                    #if roster.is_homeless():#why do i ahve this? I don;t think this is good ot have, and it could eithe never run or ruin these_date_strings
                        #roster.delete()
            return True
        else:
            return False


    def update_blackouts(self,date_dict):
        """Takes in a dictionary w/ date object as key, list w/ ["AM","PM"], or 1, as value.
        These are all of the blackouts that *shoud* exist. Takes dict and creates and deletes as appropriate."""
        existing_blackouts=self.blackout.all()
        bo_dict={}
        date_dict_keys=date_dict.keys()
        for bo in existing_blackouts:
            string_of_date=bo.date.strftime("%B %d, %Y")
            if string_of_date not in bo_dict:
                bo_dict[string_of_date]=[bo.ampm]
            else:
                temp=bo_dict.get(string_of_date)
                temp.append(bo.ampm)
                bo_dict[string_of_date]=list(temp)

        #make new ones
        for date,ampmlist in date_dict.iteritems():
            for ampmitem in ampmlist:
                date_object = datetime.datetime.strptime(date, "%B %d, %Y")
                Blackout.objects.get_or_create(registrant=self,ampm=ampmitem,date=date_object)

        #delete old ones
        for date,ampmlist in bo_dict.iteritems():
            date_object = datetime.datetime.strptime(date, "%B %d, %Y")
            if date not in date_dict:
                Blackout.objects.filter(registrant=self,date=date_object).delete()
            else:
                equivolent_date_dict_value=date_dict.get(date)

                for ampmitem in ampmlist:
                    if ampmitem not in equivolent_date_dict_value:
                        Blackout.objects.filter(registrant=self,date=date_object,ampm=ampmitem).delete()


    def save(self, *args, **kwargs):
        '''custom functions: removes non-ascii chars and punctuation from names
        makes most_upcoming con the con, if none supplied
        if no user, finds user with same email and matches, or creates one'''
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
post_save.connect(update_user_fl_name, sender=Registrant)
post_save.connect(match_user, sender=Registrant)
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
        #http://stackoverflow.com/questions/1931008/is-there-a-clever-way-to-get-the-previous-next-item-using-the-django-orm
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
        '''custom functions: removes non-ascii chars and punctuation from names
        makes most_upcoming con the con, if none supplied
        if no user, finds user with same email and matches, or creates one'''
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
