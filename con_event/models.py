import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import (
        pre_save, post_save, post_delete, pre_delete
        )
from django.utils import timezone

from con_event.signals import (update_user_fl_name, delete_homeless_user,
        clean_registrant_import, match_user, sync_reg_permissions)
from rcreg_project.extras import remove_punct, ascii_only, ascii_only_no_punct
from rcreg_project.settings import BPT_Affiliate_ID
from scheduler.app_settings import MAX_CAPTAIN_LIMIT

# For blackouts
AMPM = (('AM', 'AM'), ('PM', 'PM'))

# For challenges and trainings.
LOCATION_TYPE = (
        ('Flat Track', 'Flat Track'), ('Banked Track', 'Banked Track'),
        ('EITHER Flat or Banked Track', 'EITHER Flat or Banked Track'),
        ('Off Skates Athletic Training', 'Off Skates Athletic Training'),
        ('Seminar/Conference Room', 'Seminar/Conference Room')
        )
LOCATION_TYPE_FILTER = (
        ('Flat Track', ['Flat Track']),('Banked Track', ['Banked Track']),
        ('EITHER Flat or Banked Track', ['Flat Track','Banked Track']),
        ('Off Skates Athletic Training', ['Off Skates Athletic Training']),
        ('Seminar/Conference Room', ['Seminar/Conference Room'])
        )
LOCATION_CATEGORY = (
        ("Competition Half Length Only", "Competition Half Length Only"),
        ("Competition Any Length", "Competition Any Length"),
        ("Training", "Training"),
        ("Training or Competition", "Training or Competition"),
        ("Classroom", "Classroom")
        )
LOCATION_CATEGORY_FILTER = (
        ("Competition Half Length Only", ["Competition Half Length Only"]),
        ("Competition Any Length", ["Competition Any Length","Competition \
                Half Length Only", "Competition","Training or Competition"]),
        ("Training",["Training", "Training or Competition"]),
        ("Training or Competition", ["Training or Competition", "Training", \
            "Competition", "Competition Half Length Only",
            "Competition Any Length"]), ("Classroom", ["Classroom"]
            )
        )

# For matching criteria
GENDER = (('Female', 'Female'), ('Male', 'Male'), ('NA/Coed','NA/Coed'))
SKILL_LEVEL_SK8R = (
        (None, 'NA'), ('D', 'Rookie'), ('C', 'Beginner'),
        ('B', 'Intermediate'), ('A', 'Advanced')
        )
SKILL_LEVEL_ACT = (
        (None, "No skill restrictions; all levels welcome"),
        ('ABC', 'All Contact Safe (A-C)'),
        ('CO', 'Beginner Only- no Coed (C)'),
        ('BC', 'Beginner/Intermediate Only (B-C)'),
        ('BO', 'Intermediate Only (B)'),
        ('AB', 'Intermediate / Advanced Only (A-B)'),
        ('AO', 'Advanced Only (A)')
        )

# This weirdness below is neccesary, don't touch it.
# Unless you're smarter than I am, which you may very well be.
SKILL_LEVEL_TNG = tuple(list(SKILL_LEVEL_ACT[:2])
        + [tuple(SKILL_LEVEL_ACT[-2])])
SKILL_LEVEL_CHG = tuple([tuple(SKILL_LEVEL_ACT[0])]
        + list(SKILL_LEVEL_ACT[2:]))
# end weirdness.

SKILL_LEVEL_GAME = SKILL_LEVEL_CHG
SKILL_LEVEL = SKILL_LEVEL_SK8R + SKILL_LEVEL_ACT
PASS_TYPES = (('MVP', 'MVP'), ('Skater', 'Skater'), ('Offskate', 'Offskate'))


#===============================================================================
class Country(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    slugname = models.CharField(max_length=3,unique=True)

    #---------------------------------------------------------------------------
    def __unicode__(self):
       return "%s (%s)" % (self.name, self.slugname)

    #---------------------------------------------------------------------------
    class Meta:
        ordering = ['name']


#===============================================================================
class State(models.Model):
    slugname = models.CharField(max_length=4, primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    country = (models.ForeignKey(
            Country, null=True, blank=True, on_delete=models.SET_NULL)
            )

    #---------------------------------------------------------------------------
    def __unicode__(self):
       return "%s (%s)" % (self.name, self.slugname)

    #---------------------------------------------------------------------------
    class Meta:
        ordering = ['name']


#===============================================================================
class ConManager(models.Manager):

    #---------------------------------------------------------------------------
    def upcoming_cons(self):
        '''Gets list of cons that are coming soonest without having ended
        more than 7 days ago. I chose 7 arbitrarily, assuming no one will be
        adding stuff more than a week after a con, but wanting to leave room
        to potentially prepare for more than 1 Con per year.
        Will always return a list, even if an empty one.'''

        cutoff = datetime.date.today() - datetime.timedelta(days=7)
        upcoming = (list(Con.objects.filter(end__gte=datetime.date(
                cutoff.year, cutoff.month, cutoff.day)).order_by('start'))
                )

        return upcoming

    #---------------------------------------------------------------------------
    def past_cons(self):
        '''Gets list of cons whose end date is more than 1 week from today'''

        cutoff = datetime.date.today() + datetime.timedelta(days=7)
        past = (list(Con.objects.filter(end__lte=datetime.date(
                cutoff.year, cutoff.month, cutoff.day)).order_by('-start'))
                )

        return past

    #---------------------------------------------------------------------------
    def most_upcoming(self):
       '''Gets single most upcoming Con, without having ended more than
       7 days ago. Dependont on/see upcoming_cons above.
       If no upcoming Cons, returns None'''

       upcoming = self.upcoming_cons()
       try:
           most_upcoming_con = upcoming[0]
       except:
           most_upcoming_con = Con.objects.latest('start')

       return most_upcoming_con

    #---------------------------------------------------------------------------
    def most_recent(self):
       '''Gets single most recent past Con, having ended more than 7 days ago.
       Dependont on/see past_cons above. If no past Cons, returns None'''

       past = self.past_cons()

       try:
           most_recent_con = past[0]
           return most_recent_con
       except:
           return None


#===============================================================================
class Con(models.Model):

    # General con data
    city = models.CharField(max_length=100, default="Las Vegas")
    state = (models.ForeignKey(
            State,null=True, blank=True, on_delete=models.SET_NULL)
            )
    country = (models.ForeignKey(
            Country, null=True, blank=True, on_delete=models.SET_NULL)
            )
    start = models.DateField(auto_now=False, auto_now_add=False)
    venue = models.ManyToManyField("scheduler.Venue", blank=True)
    end = models.DateField(auto_now=False, auto_now_add=False)
    year = models.IntegerField()

    # Determines when users are allowed to do thigns
    challenge_submission_start = (models.DateField(
            auto_now=False, auto_now_add=False, null=True, blank=True)
            )
    training_submission_end = (models.DateField(
            auto_now=False, auto_now_add=False, null=True, blank=True)
            )
    sched_visible = models.BooleanField(default=False)
    sched_final = models.BooleanField(default=False)
    hoursb4signup = models.FloatField(default=2.0)
    morning_class_cutoff = (models.TimeField(
            auto_now=False, auto_now_add=False, null=True, blank=True)
            )
    dayb4signup_start = (models.TimeField(
            auto_now=False, auto_now_add=False, null=True, blank=True)
            )

    # Unnecessary crap.
    BPT_event_id = models.CharField(max_length=100, null=True, blank=True)
    ticket_link = models.URLField(null=True, blank=True)
    hotel_book_link = models.URLField(null=True, blank=True)

    objects = ConManager()

    #---------------------------------------------------------------------------
    def __unicode__(self):
       return "%s %s" % (self.year, self.city)

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ('-start',)
        unique_together = ('city', 'year')

    #---------------------------------------------------------------------------
    def get_event_link(self):
        """Creates link, including affiliate ID, for RC ticket purchase.
        Ivanna decided she preferred to send them to the RollerCon site first.
        I don't think this ended up being used anywhere.
        """

        if self.BPT_event_id:
            BPT_General_link = 'http://www.brownpapertickets.com/'
            link = (BPT_General_link + 'ref/' + BPT_Affiliate_ID
                    + '/event/' + self.BPT_event_id
                    )
            return link
        else:
            return None

    #---------------------------------------------------------------------------
    def schedule_final(self):
        """Returns True is schedule for con is final, otherwise false.
        Used to tell users is scheudle is final or tentative,
        and is schedule is ifnal, can't un-submit their scheduled challenge.
        """
        # This method was written before the field was created.
        # I should find everywhere it's used and just replace it w/ field.
        # Don't know where all are, don't care enough to risk missing a few

        if self.sched_final:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def get_unscheduled_acts(self):
        """Gathers unscheduled challenges and trainings so they can be culled
        by Khleesi after the schedule is final. Schedule must be final,
        else only empty lists returned.
        """

        c_no_os = []
        t_no_os = []

        if self.sched_final:
            # Avoid circular import
            from scheduler.models import Challenge, Training
            dead_chals = Challenge.objects.filter(con=self)
            for c in dead_chals:
                if c.occurrence_set.all().count() < 1:
                    c_no_os.append(c)

            dead_trains = Training.objects.filter(con=self)
            for t in dead_trains:
                if t.occurrence_set.all().count() < 1:
                    t_no_os.append(t)

        return c_no_os, t_no_os

    #---------------------------------------------------------------------------
    def can_submit_chlg_by_date(self):
        """Checks to see if there is a challenge submission date,
        and that date has passed.
        Does not check if received too many submissions already.
        """

        can_submit = False
        if self.challenge_submission_start:
            if self.challenge_submission_start <= datetime.date.today():
                can_submit = True

        return can_submit

    #---------------------------------------------------------------------------
    def can_submit_chlg(self):
        """Checks both if challenge submission start date has passed,
        and if submission isn't closed due to too many submissions.
        """

        from scheduler.models import Challenge  # Avoid circular import
        can_submit = self.can_submit_chlg_by_date()

        if can_submit:
            submission_full = Challenge.objects.submission_full(self)
            if submission_full:
                can_submit = False

        return can_submit

    #---------------------------------------------------------------------------
    def can_submit_trng_by_date(self):
        """Checks to see if there is a training submission end date,
        and if that date has passed. Does not check if received too many
        trainings already (currently no such thing as too many trainings).
        """

        can_submit = False
        if self.training_submission_end:
            if self.training_submission_end >= datetime.date.today():
                can_submit = True
        return can_submit

    #---------------------------------------------------------------------------
    def get_date_range(self):
        """Returns list of days between, and including, con start-end."""

        date_list = []
        if self.start and self.end:
            day = self.start
            delta = datetime.timedelta(days=1)
            stop = self.end + delta
            while day < stop:
                date_list.append(day)
                day += delta

        return date_list

    #---------------------------------------------------------------------------
    def get_locations(self):
        """Returns list of all locations associated w/ con.
        Used a lot in swingtime calendar & scheduling.
        """

        from scheduler.models import Location  # Avoid circular import
        venues = self.venue.all()
        locations = []
        for v in venues:
            for l in v.location_set.all():
                if l not in locations:
                    locations.append(l)

        return locations

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """Applies a bunch of defaults that probably will not change from year
        to year, but could maybe concievably possibly.
        """

        if self.year != self.start.year:
            self.year = self.start.year

        if self.start:
            if (not self.challenge_submission_start or
                    not self.training_submission_end
                    ):
                month = self.start.month - 4
                # If con is at end of July,
                # this will make chal submission start 3/1
                # and training submisison end 5/15
                # but leaving it open in case plan another con at other time
                if not self.challenge_submission_start:
                    dt = datetime.date(self.start.year, month, 1)
                    self.challenge_submission_start = dt
                if not self.training_submission_end:
                    dt2 = datetime.date(self.start.year, month + 2, 15)
                    self.training_submission_end = dt2

        if not self.morning_class_cutoff:
            self.morning_class_cutoff = datetime.time(hour=9, minute=30)

        if not self.dayb4signup_start:
            self.dayb4signup_start=datetime.time(hour=21, minute=30)

        if not self.country:
            self.country = Country.objects.get(name="United States")
            self.state = State.objects.get(name="Nevada")

        # Determines what shows up in the dropdown on index page.
        if not self.hotel_book_link:
            self.hotel_book_link = (
                    "http://rollercon.com/register/hotel-reservations/"
                    )
        if not self.ticket_link:
            self.ticket_link = (
                    "http://rollercon.com/register/rollercon-pass/"
                    )

        super(Con, self).save()


#===============================================================================
class Blackout(models.Model):

    registrant = models.ForeignKey('Registrant', related_name="blackout")
    date = models.DateField()
    ampm = models.CharField(max_length=100, choices=AMPM)

    #---------------------------------------------------------------------------
    def __unicode__(self):

        return "%s %s (%s)" % (self.registrant, self.date, self.ampm)

    #---------------------------------------------------------------------------
    def make_temp_o(self):
        """Makes a temporary, unsaved occurrence from blackout,
        for use in auto scheduling to indicate person busy at this time.
        """

        from swingtime.models import Occurrence  # Avoid circular import

        if self.ampm == "AM":
            start_time = (datetime.datetime(
                    self.date.year, self.date.month, self.date.day, 0, 30)
                    )
            end_time = (datetime.datetime(
                    self.date.year, self.date.month, self.date.day, 11, 29)
                    )
        elif self.ampm == "PM":
            start_time = (datetime.datetime(
                    self.date.year, self.date.month, self.date.day, 12, 30)
                    )
            end_time = (datetime.datetime(
                    self.date.year, self.date.month, self.date.day, 23, 29)
                    )

        tempo = Occurrence(start_time=start_time, end_time=end_time)

        return tempo

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ('registrant', 'date')
        unique_together = ('registrant', 'date', 'ampm')


#===============================================================================
class Matching_Criteria(models.Model):
    """"Used to match registrants to activities.
    Registrant and Roster inherit from it.
    """

    con = (models.ForeignKey(
            Con, null=True, blank=True, on_delete=models.SET_NULL)
            )
    skill = (models.CharField(
            max_length=30, null=True, blank=True, choices=SKILL_LEVEL)
            )
    gender = (models.CharField(
            max_length=30, choices=GENDER, default=GENDER[0][0])
            )
    intl = models.NullBooleanField(default=False)

    #---------------------------------------------------------------------------
    def skills_allowed(self):
        """Used for rosters to indicate which skill can be registered."""

        if self.skill:
            allowed = list(self.skill)
            if "O" in allowed:
                allowed.remove("O")
        else:
            allowed = ["A","B","C","D"]

        return allowed

    #---------------------------------------------------------------------------
    def skill_display(self):
        """Makes it so don't see A0, just A, or AB, etc. """

        prettify = ''.join(self.skills_allowed())

        return prettify

    #---------------------------------------------------------------------------
    def skill_tooltip_title(self):
        """Used in templates to tell people with words what the symbols mean."""

        if self.skill:
            allowed = self.skills_allowed()
            allowed.sort(reverse=True)
            skill_dict = dict(SKILL_LEVEL)
            str_base = "Registrant must identify skill as"
            str_end = " in Profile in order to register"
            str_mid = ""
            for item in allowed:
                if item:
                    displayable = skill_dict.get(item)
                    if item == allowed[-1]:
                        item_str = " or " + displayable
                    else:
                        item_str = " " + displayable + ","

                str_mid += item_str
            return str_base+str_mid + str_end
        else:
            return "No skill restrictions for registration"

    #---------------------------------------------------------------------------
    def skill_icon(self):
        """Returns icon. Localized here so only have to change once, if ever."""

        if not self.skill:

            return "glyphicon icon-universal-access"

    #---------------------------------------------------------------------------
    def intl_icon(self):
        """Returns icon. Localized here so only have to change once, if ever."""

        if self.intl:
            return "glyphicon icon-globe-alt"
        else:
            return "glyphicon icon-universal-access"

    #---------------------------------------------------------------------------
    def intl_text(self):
        """Localized here so only have to change once, if ever."""

        if self.intl:
            return "International"
        else:
            return None

    #---------------------------------------------------------------------------
    def intl_tooltip_title(self):
        """Localized here so only have to change once, if ever."""

        if self.intl:
            intl_text = ("Registrant must qualify as 'International' in order \
                    to register. Any MVP can audit and non-INTL auditing \
                    skaters MIGHT be allowed to participate as if registered \
                    if space is available.")
        else:
            intl_text = "No location restrictions for registration"

        return intl_text

    #---------------------------------------------------------------------------
    def gender_icon(self):
        """Localized here so only have to change once, if ever."""

        if self.gender == GENDER[0][0]:  #If Female
            return "fa fa-venus"
        elif self.gender == GENDER[1][0]:  # If male
            return "fa fa-mars"
        elif self.gender == GENDER[2][0]:  # If na/coed
            return "fa fa-venus-mars"


    #---------------------------------------------------------------------------
    def gender_text(self):
        """Localized here so only have to change once, if ever."""

        if self.gender == GENDER[0][0]:  # If Female
            return "Female"
        elif self.gender == GENDER[1][0]:  # If male
            return "Male"
        elif self.gender == GENDER[2][0]:  #If na/coed
            return "NA/Coed"

    #---------------------------------------------------------------------------
    def gender_tooltip_title(self):
        """Localized here so only have to change once, if ever."""

        if self.gender == GENDER[0][0]:  # If Female
            gender_tt = ("Registrant must identify as 'Female' in Profile \
                        in order to register")
        elif self.gender == GENDER[1][0]:  # If male
            gender_tt = ("Registrant must identify as 'Male' in Profile in \
                        order to register")
        elif self.gender == GENDER[2][0]:  #If na/coed
            gender_tt = "No gender restrictions for registration"

        return gender_tt

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        if not self.intl:
            # I don't like None, I just leave it for default select widget
            self.intl = False

        super(Matching_Criteria, self).save()

    #---------------------------------------------------------------------------
    class Meta:

        abstract = True


#===============================================================================
class RegistrantManager(models.Manager):

    #---------------------------------------------------------------------------

    ######wha tthe fuck is this doing here? thi looks like it shoud be for roster.

    def eligible_sk8ers(self, roster):
        """roster relates to training or challenge roster.
        Returns list of eligible registrants. Checks gender, intl, skill, & con.
        In retrospect I don't know why this is here and not MatchingCriteria.
        Too late to change, I guess.
        """

        from scheduler.models import Challenge  # Avoid circular import

        # Works regardless of Roster or TrainingRoster
        already_registered = list(roster.participants.all())

        if hasattr(roster, 'captain'):
            # Makes sure people on opposing team can't be selected.
            challenge_set = (list(Challenge.objects.filter(
                    Q(roster1=roster) | Q(roster2=roster)
                    )))
            opposing_skaters = []
            for c in challenge_set:
                for r in [c.roster1, c.roster2]:
                    if r and r != roster and r.participants:
                        for skater in r.participants.all():
                            opposing_skaters.append(skater)
            already_registered += opposing_skaters

        if hasattr(roster, 'captain'):#if is challenge roster
            eligibles = (Registrant.objects.filter(
                    pass_type__in=roster.passes_allowed(),
                    con=roster.con,
                    gender__in=roster.genders_allowed(),
                    intl__in=roster.intls_allowed(),
                    skill__in=roster.skills_allowed())
                    .exclude(id__in=[o.id for o in already_registered])
                    )

        else:#if is TrainingRoster:
            if roster.registered:
                training = roster.registered.training
                eligibles = (Registrant.objects.filter(
                        pass_type__in=training.passes_allowed(),
                        con=training.con,
                        intl__in=roster.intls_allowed(),
                        skill__in=training.skills_allowed())
                        .exclude(id__in=[o.id for o in already_registered])
                        )
            elif roster.auditing:
                training = roster.auditing.training
                eligibles = (Registrant.objects.filter(
                        con=training.con)
                        .exclude(id__in=[o.id for o in already_registered])
                        )

        return eligibles

#===============================================================================
class Registrant(Matching_Criteria):

    # First the necessary fields
    user = (models.ForeignKey(
            User, null=True, blank=True, on_delete=models.SET_NULL)
            )
    pass_type = (models.CharField(
            max_length=30, choices=PASS_TYPES, default='MVP')
            )
    email = models.EmailField(max_length=50)
    # Email can't be unique=true across the board bc
    # same email for same person for different cons.
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    # Unnecessary, but hard to get signed up for challenges without them
    sk8name = models.CharField(max_length=30, null=True, blank=True)
    sk8number = models.CharField(max_length=30, null=True, blank=True)

    # Helpful for INTL
    country = (models.ForeignKey(
            Country,null=True, blank=True, on_delete=models.SET_NULL)
            )
    state = (models.ForeignKey(
            State,null=True, blank=True, on_delete=models.SET_NULL)
            )

    # captaining should have been a property, probably.
    # Not important enough to change and risk breaking.
    captaining=models.IntegerField(null=True, blank=True)

    # I don't care about this data, but maybe keeping it will be helpful?
    BPT_Ticket_ID=models.CharField(max_length=30,null=True, blank=True)
    affiliation=models.CharField(max_length=100, null=True, blank=True)
    ins_carrier=models.CharField(max_length=100, null=True, blank=True)
    ins_number=models.CharField(max_length=100, null=True, blank=True)
    age_group=models.CharField(max_length=100, null=True, blank=True)
    favorite_part=models.CharField(max_length=100, null=True, blank=True)
    volunteer=models.CharField(max_length=100, null=True, blank=True)

    # I don't think internal_notes ever got used.
    internal_notes = models.TextField(null=True,blank=True)

    objects = RegistrantManager()

    #---------------------------------------------------------------------------
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

    #---------------------------------------------------------------------------
    @property
    def realname(self):

        if self.first_name and self.last_name:
            return "%s %s" % (self.first_name, self.last_name)
        else:
            return "Incomplete Name Record"

    #---------------------------------------------------------------------------
    def __unicode__(self):

        return self.name + ": " + str(self.con)

    #---------------------------------------------------------------------------
    def is_intl(self, con):
        '''Returns True if is considered INTL for supplied Con. Else, False'''

        if self.country and (self.country == con.country):
            if self.state:
                if (self.state != con.state and
                        self.state.slugname in ["HI","AK","AP"]
                        ):
                    return True
            else:
                return False

        elif not self.country:
            return False
        else:
            return True

    #---------------------------------------------------------------------------
    def can_sk8(self):

        if self.pass_type in ['MVP', 'Skater']:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def is_a_captain(self):
        """If registrant is captaining at least 1 challenge, returns list
        of challenges captained by registrant. Else, returns False.
        """

        from scheduler.models import Challenge  # Avoid circular import

        my_challenges = (Challenge.objects.filter(
                Q(roster1__captain=self) |
                Q(roster2__captain=self))
                )

        if len(my_challenges) > 0:
            return my_challenges
        else:
            return False

    #---------------------------------------------------------------------------
    def can_captain(self):
        """Returns True if # of chalenges captaining >= MAX_CAPTAIN_LIMIT,
        as specified in scheduler.app_settings.
        Else, returns False.
        """

        from scheduler.models import Challenge  # Avoid circular import

        my_challenges=(list(Challenge.objects
                .filter(is_a_game=False)
                .filter(Q(roster1__captain=self) | Q(roster2__captain=self)
                )))

        if self.can_sk8() and len(my_challenges) < MAX_CAPTAIN_LIMIT:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def criteria_conflict(self):
        """Checks to see if registrant skill or gender causes conflict
        with any rosters signed up for. If so, returns
        list of problem criteria (ex: ["gender"]),
        list of rosters in conflict (ex: [Tomboys]),
        and boolean of whether this is a captain conflict.
        Primarily used when users are making changes to their own profile.
        Nearly identical to Roster method of the same name, just
        with registrant:roster roles reversed.
        """

        problem_criteria = []
        potential_conflicts = []
        captain_conflict = False
        
        for roster in list(self.roster_set.all()):
            if self.gender not in roster.genders_allowed():
                if "gender" not in problem_criteria:
                    problem_criteria.append("gender")
                if roster not in potential_conflicts:
                    potential_conflicts.append(roster)
                if roster.captain and roster.captain == self:
                    captain_conflict = True
            if self.skill not in roster.skills_allowed():
                if "skill" not in problem_criteria:
                    problem_criteria.append("skill")
                if roster not in potential_conflicts:
                    potential_conflicts.append(roster)
                if roster.captain and roster.captain == self:
                    captain_conflict=True

        if len(potential_conflicts) > 0:
            return problem_criteria, potential_conflicts, captain_conflict
        else:
            return None, None, captain_conflict

    #---------------------------------------------------------------------------
    def conflict_sweep(self):
        """Calls criteria_conflict, removes registrant from any rosters that
        have conflicts. Doesn't let you do it if are captain.
        Primarily used when users are making changes to their own profile.
        """

        problem_criteria, potential_conflicts, captain_conflict = (
                self.criteria_conflict()
                )

        if not captain_conflict:
            if potential_conflicts:
                for roster in potential_conflicts:
                    roster.participants.remove(self)
                    roster.save()
            return True

        else:
            return False

    #---------------------------------------------------------------------------
    def update_blackouts(self, bo_tup_list):
        """Takes in a dictionary w/ date object as key, list w/ ["AM","PM"],
        or ["AM"], etc, as value, to represent when registrant is UNAVAILABLE.
        These are all of the blackouts that *should* exist.
        Takes dict and creates what is represented if doesn't exist,
        and deletes blackouts that are not represented.
        """

        existing_bo_tup_list = []
        # Gather the blackouts that exist.
        for bo in self.blackout.all():
            existing_bo_tup_list.append((bo.date,bo.ampm))

        # Make new ones
        for tup in bo_tup_list:
            if tup not in existing_bo_tup_list:
                date = tup[0]
                ampmitem = tup[1]
                (Blackout.objects.get_or_create(
                        registrant=self,ampm=ampmitem,date=date)
                        )

        # Delete unrepresented ones
        for tup in existing_bo_tup_list:
            if tup not in bo_tup_list:
                date = tup[0]
                ampmitem = tup[1]
                bo2delete = (Blackout.objects.get(
                        registrant=self, date=date, ampm=ampmitem
                        ))
                bo2delete.delete()


    #---------------------------------------------------------------------------
    def get_occurrences(self):
        """Returns list of all occurrences registrant is on roster for."""

        # Avoid circular import
        from swingtime.models import Occurrence, TrainingRoster

        reg_coach = self.user.is_a_coach()
        reg_os = []

        if reg_coach:
            coach_trains = (reg_coach.training_set
                    .filter(con=self.con)
                    .prefetch_related('occurrence_set')
                    )
            for t in coach_trains:
                reg_os += list(t.occurrence_set.all())

        reg_ros = list(self.roster_set.all())
        chal = []
        for ros in reg_ros:
            chal += list(ros.roster1.all())
            chal += list(ros.roster2.all())

            for c in chal:
                for o in c.occurrence_set.all(): #Otherwise it gets added 2x
                    if o not in reg_os:
                        reg_os.append(o)

        reg_os.sort(key=lambda o: o.start_time)

        return reg_os

    #---------------------------------------------------------------------------
    def is_occupied(self,pending_o):
        """Takes in pending occurrence, checks to see if it conflicts w/
        anything registrant is doing at moment +/- 30 mins.
        Returns list of occurrences, or False. Used by in scheduling.
        """

        # Avoid circular import
        from swingtime.models import Occurrence
        from scheduler.models import Challenge, Training,Coach

        sk8er_ros = self.roster_set.all()
        sk8er_chal = (list(Challenge.objects
                .filter(RCaccepted=True)
                .filter(Q(roster1__in=sk8er_ros) | Q(roster2__in=sk8er_ros)
                )))

        if hasattr(self.user, 'coach'):
            sk8er_train = self.user.coach.training_set.filter(con=self.con)
        else:
            sk8er_train = []

        padded_end = pending_o.end_time + datetime.timedelta(minutes=30)
        padded_start = pending_o.start_time - datetime.timedelta(minutes=30)

        concurrent=(list(Occurrence.objects
                .filter(start_time__lt=padded_end, end_time__gt=padded_start
                .filter(Q(challenge__in=sk8er_chal) |
                    Q(training__in=sk8er_train))
                .exclude(pk=pending_o.pk)
                )))

        if len(concurrent) > 0:
            return concurrent
        else:
            return False

    #---------------------------------------------------------------------------
    def is_occupied_coaching(self,pending_o):
        """Same as is_occupied, but only cares if they are coaching at that
        moment. Challenges aren't looked for.
        """
        # Avoid circular import
        from swingtime.models import Occurrence
        from scheduler.models import Challenge, Training,Coach

        sk8er_ros = self.roster_set.all()
        sk8er_chal =(list(Challenge.objects
                .filter(RCaccepted=True)
                .filter(Q(roster1__in=sk8er_ros) |  Q(roster2__in=sk8er_ros)
                )))

        if hasattr(self.user, 'coach'):
            sk8er_train = self.user.coach.training_set.filter(con=self.con)

            padded_end = pending_o.end_time + datetime.timedelta(minutes=30)
            padded_start = pending_o.start_time - datetime.timedelta(minutes=30)

            concurrent=(list(Occurrence.objects
                    .filter(training__in=sk8er_train)
                    .filter(start_time__lt=padded_end,
                            end_time__gt=padded_start)
                    .exclude(pk=pending_o.pk)
                    ))

            if len(concurrent) > 0:
                return concurrent
            else:
                return False
        else:
            return False

    #---------------------------------------------------------------------------
    def check_conflicts(self):
        """Gets occurrences registrant is involved with,
        checks to see if any are at conflicting times.
        Splits into 2 lists: conflict and free.
        +/- 30 minute window counts as conflict.
        Returns both, even if empty.
        """

        # Avoid circular import
        from swingtime.models import Occurrence
        from scheduler.models import Challenge, Training, Coach

        reg_os = self.get_occurrences()
        conflict = []
        free = []

        sk8er_ros = self.roster_set.all()
        sk8er_chal = (list(Challenge.objects
                .filter(RCaccepted=True)
                .filter(Q(roster1__in=sk8er_ros) | Q(roster2__in=sk8er_ros)
                )))

        if hasattr(self.user, 'coach'):
            sk8er_train = self.user.coach.training_set.filter(con=self.con)
        else:
            sk8er_train = []

        padded_end = pending_o.end_time + datetime.timedelta(minutes=30)
        padded_start = pending_o.start_time - datetime.timedelta(minutes=30)
        for o in reg_os:
            concurrent = (Occurrence.objects
                    .filter(start_time__lt=padded_end, end_time__gt=padded_start
                    .filter(Q(challenge__in=sk8er_chal) |
                        Q(training__in=sk8er_train))
                    .exclude(pk=o.pk)
                    ))

            if len(concurrent) < 1:
                free.append(o)
            else:
                if o not in conflict:
                    conflict.append(o)

        return conflict, free

    #---------------------------------------------------------------------------
    def get_trainings_attended(self):
        """Gets trainings registrant was on registered or auditing rosters for.
        Used for determing which can review after the con.
        """

        # Avoid circular import
        from swingtime.models import Occurrence, TrainingRoster

        trainingrosters = self.trainingroster_set.all()
        trainings = []
        for tr in trainingrosters:
            if tr.registered:
                o = tr.registered
            elif tr.auditing:
                o = tr.auditing
            else:
                o = None  # Should never happen
            if o and o.training:
                trainings.append(o.training)

        return trainings

    #---------------------------------------------------------------------------
    def get_my_schedule_url(self):
        """Used for bosses to check someone's schedule."""

        from scheduler.views import my_schedule  # Avoid circular import

        url = "%s?registrant=%s" % (
                reverse('scheduler.views.my_schedule'),self.pk
                )

        return url

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        string_fields = [
                'first_name', 'last_name', 'sk8name', 'sk8number',
                'BPT_Ticket_ID', 'affiliation', 'ins_carrier', 'ins_number',
                'age_group', 'favorite_part', 'volunteer'
                ]

        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)

        if self.internal_notes:
            cleaned_notes = ascii_only(self.internal_notes)
            self.internal_notes = cleaned_notes

        if not self.sk8number:
            self.sk8number = "X"

        if not self.con:
            upcoming = Con.objects.most_upcoming()
            self.con = upcoming

        if self.is_a_captain():
            self.captaining = len(self.is_a_captain().exclude(is_a_game=True))
        else:
            self.captaining = 0

        if not self.intl:  # If manually made intl, fine, it'll stay.
            self.intl = self.is_intl(self.con)
        super(Registrant, self).save()

    #---------------------------------------------------------------------------
    class Meta:
        ordering = ('con', 'sk8name', 'last_name', 'first_name')
        unique_together = (
                ('con', 'email'), ('con', 'user'),
                ('con','last_name','first_name','sk8name')
                )

pre_save.connect(clean_registrant_import, sender=Registrant)
pre_save.connect(match_user, sender=Registrant)
post_save.connect(update_user_fl_name, sender=Registrant)
post_save.connect(sync_reg_permissions, sender=Registrant)
pre_delete.connect(delete_homeless_user, sender=Registrant)

#===============================================================================
class Blog(models.Model):

    headline = models.CharField(max_length=200, unique=True)
    slugname = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    user = (models.ForeignKey(
            User, limit_choices_to={'is_staff': True},
            null=True, blank=True, on_delete=models.SET_NULL)
            )
    post = models.TextField()

    #---------------------------------------------------------------------------
    def __unicode__(self):

        return "%s (%s)" % (self.headline, self.date)

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ('-date',)

    #---------------------------------------------------------------------------
    def getslugname(self):

        if not self.slugname or self.slugname == "":
            self.slugname = self.headline.replace(' ', '_')

        return self.slugname

    #---------------------------------------------------------------------------
    def get_next_and_previous(self):
        """Returns next blog object and previous, chronologically speaking."""

        try:
            next_blog = self.get_next_by_date()
        except:
            next_blog = None
        try:
            previous_blog = self.get_previous_by_date()
        except:
            previous_blog = None

        return next_blog,previous_blog

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        string_fields = ['headline']
        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)
        cleaned_post = ascii_only(self.post)
        self.post = cleaned_post

        if not self.slugname:
            self.getslugname()

        super(Blog, self).save()

    #---------------------------------------------------------------------------
    def get_absolute_url(self):

        from con_event.views import announcement  # Avoid circular import

        return reverse('con_event.views.announcement', args=[str(self.slugname)])
