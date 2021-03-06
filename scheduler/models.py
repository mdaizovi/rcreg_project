from collections import OrderedDict
from copy import deepcopy
import datetime
from datetime import timedelta
import string

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.mail import EmailMessage, send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q, F
from django.db.models.signals import pre_save, post_save, pre_delete
from django.utils import timezone

from con_event.models import (MatchingCriteria, Con, Registrant,
        LOCATION_TYPE, LOCATION_CATEGORY, GENDER, SKILL_LEVEL_CHG,
        SKILL_LEVEL_TNG, SKILL_LEVEL
        )
from rcreg_project.extras import remove_punct,ascii_only, ascii_only_no_punct
from rcreg_project.settings import (BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME,
        SECOND_CHOICE_EMAIL, SECOND_CHOICE_PW
        )
from scheduler.app_settings import (CLOSE_CHAL_SUB_AT, GAME_CAP,
        DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION
        )
from scheduler.signals import (challenge_defaults, delete_homeless_roster_chg,
        delete_homeless_roster_ros, delete_homeless_chg
        )
from swingtime.conf.swingtime_settings import (TIMESLOT_INTERVAL,
        TIMESLOT_START_TIME, TIMESLOT_END_TIME_DURATION
        )


COLORS = (("Black", "Black"), ("Beige or tan", "Beige or tan"),
        ("Blue (aqua or turquoise)", "Blue (aqua or turquoise)"),
        ("Blue (dark)", "Blue (dark)"), ("Blue (light)", "Blue (light)"),
        ("Blue (royal)", "Blue (royal)"), ("Brown", "Brown"),
        ("Burgundy", "Burgundy"), ("Gray/Silver", "Gray/Silver"),
        ("Green (dark)", "Green (dark)"), ("Green (grass)", "Green (grass)"),
        ("Green (lime)", "Green (lime)"),
        ("Green (olive or camo pattern)", "Green (olive or camo pattern)"),
        ("Orange", "Orange"), ("Pink (hot)", "Pink (hot)"),
        ("Pink (light)", "Pink (light)"), ("Purple", "Purple"), ("Red", "Red"),
        ("White", "White"), ("Yellow/gold", "Yellow/gold")
        )
GAMETYPE = (('3CHAL', '30 minute Challenge'), ('6CHAL', '60 minute Challenge'),
        ('36CHAL', '30 or 60 minute Challenge'),
        ('6GAME','60 min REGULATION or SANCTIONED Game (between two existing WFTDA/MRDA/RCDL/USARS teams)')
        )
RULESET = (('WFTDA', 'WFTDA'), ('MRDA', 'MRDA'), ('RDCL', 'RDCL'),
        ('USARS', 'USARS'), ('Other', 'Other')
        )
INTEREST_RATING = ((0, 'NA'), (1, '1: Very Low Interest'),
        (2, '2: Somewhat Low Interest'), (3, '3: Medium'),
        (4, '4: Somewhat High Interest'), (5, '5: Very High Interest')
        )
SESSIONS_TR = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
DURATION=(('0.75', '45 minutes'), ('1', '1 Hour'),
        ('1.5', 'Hour and a Half (90 minutes)'), ('2', '2 Hours (120 minutes)')
        )
SKILL_INTEREST_DICT = {'AO': 5, 'AB': 4, 'BO': 3, 'BC': 2, 'CO': 1, 'ABC': 1,
        'A': 5, 'B': 3,'C': 2, 'D': 1
        }


#===============================================================================
class Venue(models.Model):
    name = models.CharField(max_length=50, unique=True)

    #---------------------------------------------------------------------------
    def __unicode__(self):
       return self.name

    #---------------------------------------------------------------------------
    class Meta:
        ordering = ('name',)


#===============================================================================
class Location(models.Model):

    venue = models.ForeignKey(Venue, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)
    abbrv = models.CharField(max_length=50, null=True, blank=True)
    location_type = models.CharField(max_length=50, choices=LOCATION_TYPE)
    location_category = (models.CharField(
            max_length=50,null=True, blank=True, choices=LOCATION_CATEGORY
            ))

    #---------------------------------------------------------------------------
    def __unicode__(self):

       return "%s, %s" % (self.name, self.venue.name)

    #---------------------------------------------------------------------------
    def is_free(self, start_time, end_time):
        """Checks to see if location has any occurrences for the time between
        start and end provided. Returns True if no occurrences, else False.
        """

        from swingtime.models import Occurrence  #  Avoid circular import

        qs = list(Occurrence.objects.filter(
                start_time__lt=end_time,
                end_time__gt=start_time,
                location=self)
                )

        if len(qs) > 0:
            return False
        else:
            return True

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ('venue', 'name')
        unique_together = ('name', 'venue')


#===============================================================================
class Roster(MatchingCriteria):
    """Challenges/Games only"""

    cap = models.IntegerField(default=GAME_CAP)
    name = models.CharField(max_length=200, null=True, blank=True)
    captain = (models.ForeignKey(Registrant, related_name="captain", null=True,
            blank=True, on_delete=models.SET_NULL)
            )
    color = models.CharField(max_length=100, null=True, blank=True, choices=COLORS)
    can_email = models.BooleanField(default=True)
    internal_notes = models.TextField(null=True, blank=True)
    participants = models.ManyToManyField(Registrant, blank=True)

    #---------------------------------------------------------------------------
    def __unicode__(self):

        if self.name:
            return "%s %s" %( self.name, self.con)
        else:
            return "unnamed team"

    #---------------------------------------------------------------------------
    def validate_unique(self, *args, **kwargs):
        super(Roster, self).validate_unique(*args, **kwargs)

        if self.captain:
            # Note: this doesn't work for propose_new_challenge
            # because captain isn't captain yet.
            if self.captain.skill not in self.skills_allowed():
                raise ValidationError({
                    NON_FIELD_ERRORS: [
                            "Captain's skill (%s) is one which is ineligible "
                            "for team skill (%s). Please change captain, change"
                            " captain skill, or change team skill."
                            % (self.captain.skill_display(), self.skill_display()),
                            ],})
            if self.captain.gender not in self.genders_allowed():
                raise ValidationError({
                    NON_FIELD_ERRORS: [
                            "Captain's gender (%s) is one which is ineligible "
                            "for team gender (%s). Please change captain, change"
                            " captain gender, or change team gender."
                            % (self.captain.gender, self.gender),
                            ],})

        if self.coed_beginner():
            raise ValidationError({
                NON_FIELD_ERRORS: [
                        "Coed teams have a minimum skill level of Intermediate."
                        " Please raise the skill level or select a gender for "
                        "the team",
                        ],})

    #---------------------------------------------------------------------------
    @property
    def challenge_name(self):
        """Returns name of Challenge Roster is attached to.
        Should only be 1, but is possible to be more.
        """

        names = ""
        chals = list(self.roster1.all()) + list(self.roster2.all())
        for c in chals:
            names += str(c.name)+" , "
        if len(names)>2:
            names = names[:-2]  # to get rid of trailing comma

        return names

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):
        # Remove non-ascii, puncuation, from name.
        string_fields = ['name']
        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only_no_punct(att_unclean)
                setattr(self, item, cleaned_att)

        # Keep punctuation, but make ascii only.
        if self.internal_notes:
            cleaned_notes = ascii_only(self.internal_notes)
            self.internal_notes = cleaned_notes

        # Make sure captain is on the roster.
        if self.captain:
            try:  # So won't have problem with first save
                if self.captain not in self.participants.all():
                    self.participants.add(self.captain)
            except:
                pass
        super(Roster, self).save()

    #---------------------------------------------------------------------------
    def criteria_conflict(self):
        """Checks to see if roster skill or gender causes conflict
        with any skaters signed up for it. If so, returns
        list of problem criteria (ex: ["gender"]),
        list of registrants in conflict (ex: [Ivanna S Pankin]),
        and boolean of whether this is a captain conflict.
        Nearly identical to Registrant method of the same name, just
        with registrant:roster roles reversed.
        """

        problem_criteria = []
        potential_conflicts = []
        captain_conflict = False
        genders_allowed = self.genders_allowed()
        skills_allowed = self.skills_allowed()

        def capt_confl(problem_criteria, potential_conflicts, captain_conflict):
            """Captain conlict check on its own for when roster is created.
            At that point there is no such thing as roster.participants,
            but still need to make sure captain is not trying to make a roster
            for which they would be ineligible.
            """

            if self.captain and (self.captain.gender not in genders_allowed):
                captain_conflict = True
                if "gender" not in problem_criteria:
                    problem_criteria.append("gender")
                    if self.captain not in potential_conflicts:
                        potential_conflicts.append(self.captain)
            if self.captain and (self.captain.skill not in skills_allowed):
                captain_conflict = True
                if "skill" not in problem_criteria:
                    problem_criteria.append("skill")
                if self.captain not in potential_conflicts:
                    potential_conflicts.append(self.captain)

            return problem_criteria, potential_conflicts, captain_conflict

        try:
            participants = list(self.participants.all())
            if len(participants) > 0:
                for skater in list(self.participants.all()):
                    if skater.gender not in genders_allowed:
                        if "gender" not in problem_criteria:
                            problem_criteria.append("gender")
                        if skater not in potential_conflicts:
                            potential_conflicts.append(skater)
                        if self.captain and skater == self.captain:
                            captain_conflict=True
                    if skater.skill not in skills_allowed:
                        if "skill" not in problem_criteria:
                            problem_criteria.append("skill")
                        if skater not in potential_conflicts:
                            potential_conflicts.append(skater)
                        if self.captain and skater == self.captain:
                            captain_conflict=True
            else:
                problem_criteria, potential_conflicts, captain_conflict = (
                        capt_confl(problem_criteria, potential_conflicts,
                        captain_conflict)
                        )
        except:  # If roster not saved yet, can't use m2m yet.
            problem_criteria, potential_conflicts, captain_conflict = (
                    capt_confl(problem_criteria, potential_conflicts,
                    captain_conflict)
                    )

        if len(potential_conflicts) > 0:
            return problem_criteria, potential_conflicts, captain_conflict
        else:
            return None, None, captain_conflict

    #---------------------------------------------------------------------------
    def conflict_sweep(self):
        """Calls criteria_conflict, dropping from roster participants any
        registrants that have conflicts, except captain.
        """

        problem_criteria, potential_conflicts, captain_conflict = (
                self.criteria_conflict()
                )

        if not captain_conflict:
            if potential_conflicts:
                for skater in potential_conflicts:
                    self.participants.remove(skater)
            return True

        else:
            return False

    #---------------------------------------------------------------------------
    def has_number_dupes(self):
        """Checks to see if same sk8number is in roster twice. Checks string.
        Returns list of dupes, or False"""

        numbers = []
        dupes = []

        for s in self.participants.all():
            if s.sk8number in numbers:
                dupes.append(s.sk8number)
            numbers.append(s.sk8number)

        if len(dupes) > 0:
            number_dupes = dupes
        else:
            number_dupes = False

        return number_dupes

    #---------------------------------------------------------------------------
    def get_maxcap(self):
        """checks if Roster has max cap specified. If not, supplies default."""
        if self.cap:
            maxcap = self.cap
        else:
            maxcap = GAME_CAP

        return maxcap

    #---------------------------------------------------------------------------
    def spacea(self):
        """Gets maxcap, checks if participants are fewer. Returns number of
        spacea available, or False.
        """

        maxcap = self.get_maxcap()
        spacea = maxcap - self.participants.count()

        if spacea > 0:
            return spacea
        else:
            return False

    #---------------------------------------------------------------------------
    def add_sk8er_challenge(self, skater_pk):
        """Ads registrant to roster, saves roster.
        Ivanna special request-- if registrant is bus coaching in a scheduled
        training, can't be added to roster.
        If successful, returns skater, None, False. If unsucessful, returns
        None, skater, and string explaining why unsuccessful.
        """

        add_fail_reason = False
        is_free = True
        skater_added = None
        add_fail = None

        if self.spacea():
            try:
                skater_added = Registrant.objects.get(pk=skater_pk)
                my_cs = list(self.roster1.all()) + list(self.roster2.all())
                my_os = []
                concurrent = []
                for c in my_cs:
                    my_os += list(c.occurrence_set.all())

                for o in my_os:
                    occupied = skater_added.is_occupied_coaching(o)
                    if occupied:
                        concurrent += occupied

                if len(concurrent) > 0:
                    add_fail = skater_added
                    add_fail_reason = (" because %s is busy with "
                            % (skater_added.name)
                            )
                    ci = 0
                    for c in concurrent:
                        ci += 1
                        if ci > 1:
                            if ci == len(concurrent):
                                add_fail_reason += ", & "+c.name
                            else:
                                add_fail_reason += ", "+c.name
                        else:
                            add_fail_reason += c.name

                if not add_fail:
                    self.participants.add(skater_added)
                    self.save()
            except:  # Not expecting any failures, just in case.
                try:
                    add_fail = Registrant.objects.get(pk=skater_pk)
                except:
                    add_fail = True
                    add_fail_reason = "Error selecting skater, please try again"

        else:  # If not spacea
            add_fail = Registrant.objects.get(pk=skater_pk)
            add_fail_reason = " because the roster is full."

        return skater_added, add_fail, add_fail_reason

    #---------------------------------------------------------------------------
    def remove_sk8er_challenge(self, skater_pk):
        """Removes skater from roster, saves roster. If succeessful, returns
        skater and None. If failure, returns None and skater.
        """

        skater_remove = None
        remove_fail = None
        try:
            try:
                skater_remove = Registrant.objects.get(pk=skater_pk)
                if skater_remove != self.captain:
                    self.participants.remove(skater_remove)
                    self.save()
                else:
                    remove_fail = skater_remove
            except:
                remove_fail = Registrant.objects.get(pk=skater_pk)
        except:
            pass

        return skater_remove, remove_fail

    #---------------------------------------------------------------------------
    def opponent_skills_allowed(self):
        """Non-game rosters can only play opponents within 1 skill level of
        themselves. Returns list of permissible opponents skill level displays, as
        determined by own skill.
        ex: roster w/ AO returns ['A','B']. None returns ['ABCD']
        Used in edit_challenge view.
        """

        allowed = []
        skillphabet = ["AO", "AB", "BO", "BC", "CO"]

        if self.skill:
            skill_index = skillphabet.index(self.skill)
            for i in range(skill_index - 1, skill_index + 2):
                if i >= 0 and i < len(skillphabet):
                    allowed.append(skillphabet[i])
        else:
            allowed = list(skillphabet + [None])

        return allowed

    #---------------------------------------------------------------------------
    def opp_cap_skills_allowed(self):
        """Calls opponent_skills_allowed to find out which skills opposing
        captains can have. Is same, but minus the O.
        Used when filtering captains that can be challenged, in edit_challenge.
        """

        allowed = self.opponent_skills_allowed()
        trimmed = []
        for s in allowed:
            try:
                for l in s:
                    if l not in trimmed and l!= "O":
                        trimmed.append(l)
            except:
                trimmed.append(s)

        return trimmed

    #---------------------------------------------------------------------------
    def genders_allowed(self):
        """Coed teams can have registrants of any gender. Otherwise needs to
        match, but registrants who select na/coed can play on any team.
        Returns list of which genders are allowed on the roster.
        """

        if self.gender == 'NA/Coed':
            allowed = ["Female", "Male", "NA/Coed"]
        else:
            allowed = ["NA/Coed", self.gender]

        return allowed

    #---------------------------------------------------------------------------
    def intls_allowed(self):
        """If roster is INTL, only INTL registrants can be added.
        Returns list of which INTL statuses can be added to roster.
        """

        if self.intl:
            allowed = [True]
        else:
            allowed = [True, False, None]

        return allowed

    #---------------------------------------------------------------------------
    def passes_tooltip_title(self):

        pass_list = self.passes_allowed()
        pass_string = ""
        if len(pass_list) > 1:
            if len(pass_list) > 2:
                for item in pass_list[:-1]:
                    pass_string+=item + ", "
            else:
                pass_string += pass_list[0]
            pass_string += " or " + pass_list[-1]
        else:
            pass_string = pass_list[0]

        tooltip_title = base_str + (" Registrant must have %s pass in order to\
                register"%(pass_string)
                )
        return tooltip_title

    #---------------------------------------------------------------------------
    def editable_by(self):
        """Returns list of users that can edit Roster. For adding/removing
        roster participants. Editors: Bosses, NSOs, captain.
        """

        allowed_editors=list(User.objects.filter(groups__name__in=[
                BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME,'NSO'
                ]))

        if self.captain:
            allowed_editors.append(self.captain.user)

        return allowed_editors

    #---------------------------------------------------------------------------
    def nearly_homeless(self):
        """This is for reject warning, to check if rejecting this challenge will
        delete roster. Mostly for Game rosters, obvious for Challenge Rosters.
        Returns True if roster has no other challenges and will be deleted if
        challenge is rejected.
        """

        r1 = list(self.roster1.all())
        r2 = list(self.roster2.all())
        rs = r1 + r2

        if len(rs) <= 1:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def is_homeless(self):
        """Returns True if roster has no challenges."""

        r1 = list(self.roster1.all())
        r2 = list(self.roster2.all())
        rs = r1 + r2

        if len(rs) <= 0:
            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def coed_beginner(self):
        """Not allowed to have a roster that is coed nd beginner. If this is
        attempted, tries to move skill up. If captain is not skilled enough,
        matches captain gender. If captain is coed beginner,
        Does not run for Games, as all Games are essentially coed-beginner.
        """

        coed_conflict = False

        if self.gender == 'NA/Coed':
            forbidden_skills = [None, False, 'C', 'CO', 'BC', 'ABC']

            if self.skill in forbidden_skills:
                coed_conflict = True

        return coed_conflict

    #---------------------------------------------------------------------------
    def restore_defaults(self):
        """Makes the roster blank, after having been rejected."""

        self.captain = None
        self.participants.clear()
        self.name = None
        self.color = None
        self.can_email = True
        self.save()

    #---------------------------------------------------------------------------
    def defaults_match_captain(self):
        """Roster defaults changed to match captain. Used when first created."""

        if self.captain:
            self.gender = self.captain.gender
            cap_skill = str(self.captain.skill)
            # roster skills are a little different that registrant skills.
            self.skill = cap_skill + "O"
            self.con = self.captain.con
            self.save()
        else:
            self.restore_defaults()

    #---------------------------------------------------------------------------
    def clone_roster(self, recipient=None):
        """Makes (existing) self look just like original roster, including
        participants. Does not clone internal_notes.
        Returns new roster after having saved it.
        """
        if not recipient:
            recipient = Roster()
        for attr in ['cap', 'name', 'gender', 'intl', 'skill', 'captain',
                'color', 'can_email'
                ]:
            value=getattr(self, attr)
            setattr(recipient, attr, value)
        recipient.save()
        recipient.participants.add(*self.participants.all())
        recipient.save()

        return recipient

    #---------------------------------------------------------------------------
    def get_edit_url(self):

        return reverse('scheduler.views.edit_roster', args=[str(self.pk)])

    #---------------------------------------------------------------------------
    def email_captain(self, sending_user, message):
        """if captain has agreed to accept emails and has a user and user has an
        email address. By default all registrant should have users and email
        addresses. But who knows, maybe one will get deleted.
        Takes user that wants to email, tries to email.
        Returns True if successful.
        """

        email_success = False
        captain=self.captain.user

        if (self.can_email and captain and captain.email):
            subject = ("%s, %s has sent you a message through the RollerTron "
                    "site!" % (captain.first_name, sending_user.first_name)
                    )
            message_body = ("Message below. Please respond to %s, not to us. "
                    "\n\n\n%s" % (sending_user.email, message)
                    )
            email = EmailMessage(
                    subject=subject,
                    body=message_body,
                    to=[captain.email],
                    reply_to=[sending_user.email]
                    )
            try:
                email.send(fail_silently=False)
                email_success = True
            except:
                try:
                    send_mail(
                            subject,
                            message_body,
                            from_email=SECOND_CHOICE_EMAIL,
                            recipient_list=[captain.email],
                            fail_silently=False,
                            auth_user=SECOND_CHOICE_EMAIL,
                            auth_password=SECOND_CHOICE_PW
                            )
                    email_success = True
                except:
                    email_success = False

        return email_success

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ("-con__start", 'name', 'captain')

#-------------------------------------------------------------------------------
post_save.connect(delete_homeless_roster_ros, sender=Roster)


#===============================================================================
class Activity(models.Model):
    # Inherited by challenge and training
    name = models.CharField(max_length=200)
    con = models.ForeignKey(Con,on_delete=models.PROTECT)
    location_type = models.CharField(max_length=30, choices=LOCATION_TYPE)
    RCaccepted = models.BooleanField(default=False)
    RCrejected = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=timezone.now)
    # because duration fields are reputably buggy in 1.8
    duration = models.CharField(max_length=30, choices=DURATION, null=True, blank=True)
    interest = models.IntegerField(null=True, blank=True, choices=INTEREST_RATING)

    internal_notes = models.TextField(null=True, blank=True)
    communication = models.TextField(null=True, blank=True)

    #---------------------------------------------------------------------------
    def is_a_challenge(self):
        """Tests to see if is Challenge. If else, probably a Training.
        Just wanted to stop repeating self w/ hasattr, in case ever change
        fields that dictate which it is.
        """

        if hasattr(self, 'roster1') or hasattr(self, 'roster2'):

            return True
        else:
            return False

    #---------------------------------------------------------------------------
    def is_a_training(self):
        """Tests to see if is Training If else, probably a Challenge.
        Just wanted to stop repeating self w/ hasattr, in case ever change
        fields that dictate which it is.
        """

        if hasattr(self, 'coach'):

            return True
        else:
            return False

    #---------------------------------------------------------------------------
    @property
    def data_title(self):
        """Takes info from Challenge/Training, returns title in format
        RC Ladies are accustomed to, MOSTLY. Can't include INTL.
        """

        desc = ""
        skill_text = self.skill_display().replace("ABCD", "ALL")

        if self.is_a_training():
            desc += self.name

            if self.onsk8s:
                desc += " (%s" % (skill_text)
                if not self.contact:
                    desc += " [NO Contact]"
                desc += ")"

        elif self.is_a_challenge():
            gender_display = self.gender_display().replace("NA/Coed", "Co-ed")
            desc += "%s (%s [%s])" % (self.name, skill_text, gender_display)

        return desc

    #---------------------------------------------------------------------------
    @property
    def figurehead_display(self):
        """Returns string of both captains, or all coaches."""

        fs = self.get_figurehead_registrants()
        fstr = ""
        index = 1
        for f in fs:
            if index >1:
                fstr += " & "
            fstr += f.name

            index += 1

        return fstr

    #---------------------------------------------------------------------------
    def get_default_interest(self):
        """if challenge, gets average of teams skill.
        if training, gerts average of coach skill
        to estimate interest my skill"""
        skill_list=[]

        if self.is_a_challenge():
            if self.gametype == "6GAME":
                skill_list.append(5)
            else:
                for r in [self.roster1,self.roster2]:
                    if r and r.skill:
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

    #---------------------------------------------------------------------------
    def get_figurehead_registrants(self):
        """Determines if is Training or Challange.
        If former, gets coaches. If latter, gets captains.
        Returns list of registrants.
        """

        figureheads = []
        if self.is_a_training():
            for c in (self.coach.select_related('user')
                    .prefetch_related('user__registrant_set')
                    .all()
                    ):
                for r in c.user.registrant_set.select_related('con').all():
                    if r.con == self.con:
                        figureheads.append(r)
        elif self.is_a_challenge():
            for r in [self.roster1, self.roster2]:
                if r and r.captain:
                    figureheads.append(r.captain)

        return figureheads

    #---------------------------------------------------------------------------
    def get_figurehead_blackouts(self):
        """Gets Blackouts for activity, from all coaches or captains,
        but not participants.
        """
        from con_event.models import Blackout  #  Avoid circular import
        figureheads = self.get_figurehead_registrants()
        b_outs = list(Blackout.objects.filter(registrant__in=figureheads))

        return b_outs

    #---------------------------------------------------------------------------
    def editable_by(self):
        """Returns list of Users that can edit activity
        keep in mind being captain of EITHER team makes this True
        Also, boss ladies, but no NSOs or Volunteers"""

        allowed_editors = list(User.objects.filter(groups__name__in=[
                BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME
                ]))

        figureheads = self.get_figurehead_registrants()
        for f in figureheads:
            allowed_editors.append(f.user)

        return allowed_editors

    #---------------------------------------------------------------------------
    def participating_in(self):
        """Returns list of Registrants that are on either participating roster,
        or are Coach.
        For use in Scheduling as well as seeing Communication between NSO/skaters
        """

        participating = []
        if self.is_a_training():
            for c in self.coach.select_related('user').all():
                for reg in c.user.registrant_set.select_related('con').all():
                    if reg.con == self.con:
                        participating.append(reg)

        elif self.is_a_challenge():
            for ros in [self.roster1, self.roster2]:
                if ros:
                    for sk8 in ros.participants.all():
                        participating.append(sk8)
                    if ros.captain and ros.captain not in participating:
                        participating.append(ros.captain)

        return participating

    #---------------------------------------------------------------------------
    def possible_locations(self):
        """Gets location type of activity, returns list of specific locations
        it can be in, for that Con. Based on Ivanna's specifications.
        """

        venues = self.con.venue.prefetch_related('location').all()

        if self.location_type =='Flat Track':
            if self.is_a_training():
                return list(Location.objects.filter(
                        venue__in=venues,
                        location_type='Flat Track',
                        location_category="Training")
                        )
            elif self.is_a_challenge():
                 # Games have to be in C1
                if self.gametype == "6GAME" or float(self.duration) >= 1:
                    return list(Location.objects.filter(
                            venue__in=venues,
                            location_type='Flat Track',
                            location_category="Competition Any Length")
                            )
                else:  # Can be n C1 or C2
                    return list(Location.objects.filter(
                            venue__in=venues,
                            location_type='Flat Track',
                            location_category__in=[
                                    "Competition Half Length Only",
                                    "Competition Any Length"
                                    ]
                            ))

        elif self.location_type == 'EITHER Flat or Banked Track':
            if self.is_a_training():
                return list(Location.objects.filter(
                        location_category__in=["Training","Training or Competition"],
                        venue__in=venues,
                        location_type__in=['Flat Track','Banked Track']
                        ))
            elif self.is_a_challenge():
                return list(Location.objects.filter(
                        location_category__in=["Training or Competition",
                                "Competition Half Length Only",
                                "Competition Any Length"
                                ],
                        venue__in=venues,
                        location_type__in=['Flat Track','Banked Track']
                        ))
        else:
            return list(Location.objects.filter(
                    venue__in=venues,
                    location_type=self.location_type)
                    )

    #---------------------------------------------------------------------------
    def dummy_occurrences(self,level,makedummies):
        """Makes unsaved Occurrence objects for all possible location time
        combinations for activity. Also gathers possible empty occurrances.
        """
        # This works, but it makes about 2500 on my first test run. Not Plan A.

        from swingtime.models import Occurrence  #  Avoid circular import

        dummies = []
        pls = self.possible_locations()
        if self.interest:
            proxy_interest = self.interest
        else:
            proxy_interest = self.get_default_interest()

        if self.is_a_training():
            # Make high demand classes in low interest timeslots and vice versa
            proxy_interest = abs(6 - proxy_interest)
            challenge = None
            training = self
        elif self.is_a_challenge():
            challenge = self
            training = None
        duration = float(self.duration)
        dur_delta = int(duration * 60)

        date_range = self.con.get_date_range()
        base_q = Occurrence.objects.filter(
                challenge=None,
                training=None,
                location__in=pls,
                start_time__gte=self.con.start,
                end_time__lte=self.con.end
                )

        if level == 1:
            base_q = base_q.filter(interest=proxy_interest).filter(
                    end_time=F('start_time') + timedelta(minutes=dur_delta)
                    )
        elif level == 2:
            ilist = [int(proxy_interest) - 1, int(proxy_interest), int(proxy_interest) + 1]
            base_q = base_q.filter(interest__in=ilist).filter(
                    end_time=F('start_time') + timedelta(minutes=dur_delta)
                    )

        empties=list(base_q)
        # Works, but is time consuming.
        # don't want to optimize if Ivanna doesn't care and never uses
        if makedummies:
            for d in date_range:
                day_start = datetime.datetime(
                        year=d.year,
                        month=d.month,
                        day=d.day,
                        hour=TIMESLOT_START_TIME.hour
                        )
                day_end = day_start + TIMESLOT_END_TIME_DURATION
                slot_start = day_start
                slot_end = slot_start+datetime.timedelta(minutes=dur_delta)

                while slot_end < day_end:
                    for l in pls:
                        if l.is_free(slot_start, slot_end):
                            o = Occurrence(
                                    start_time=slot_start,
                                    end_time=slot_end,
                                    location=l,
                                    challenge=challenge,
                                    training=training
                                    )
                            dummies.append(o)

                    slot_start += TIMESLOT_INTERVAL
                    slot_end += TIMESLOT_INTERVAL

        return [empties, dummies]

    #---------------------------------------------------------------------------
    def sched_conflict_score(self, level, makedummies):
        """Takes in activity, makes list of dummy occurrances.
        Checks each one for schedule conflicts, scores them so that
        each blackout is worth 100 pts, Figurehead 10, Participant 1.
        Returns ordered dict, w/ key as score, v as list of occurrences that
        match score, sorted 0-highest.
        NEW: may remove Os depending on level"""

        odict_list = []
        if self.is_a_training():
            training = self
        else:
            training = None
        if self.is_a_challenge():
            challenge = self
        else:
            challenge = None

        if int(level) < 2:
            max_score = 0
        elif int(level) == 2:
            max_score = 99
        else:
            max_score = 999999999999999999  # Arbitrary really big number

        for olist in list(self.dummy_occurrences(level=level, makedummies=makedummies)):
            if len(olist) > 0:
                conflict = {}
                for o in olist:
                    # Don't save, this is to make figurehead registrants work
                    o.training = training
                    o.challenge = challenge
                    score = 0

                    blackout_conflict = o.blackout_conflict()
                    if blackout_conflict:
                        this_score = len(blackout_conflict) * 100
                        score += this_score

                    figurehead_conflict = o.figurehead_conflict()
                    if figurehead_conflict:
                        this_score = len(figurehead_conflict) * 10
                        score += this_score

                    participant_conflict = o.participant_conflict()
                    if participant_conflict:
                        this_score = len(participant_conflict) * 1
                        score += this_score

                    if score not in conflict:
                        conflict[score] = [o]
                    else:
                        this_list = conflict.get(score)
                        this_list.append(o)
                        conflict[score] = list(this_list)
            else:
            # If empty list, otherwise uses last conflict and return wrong occurrence
                conflict = {}

            score_list = list(conflict.keys())
            score_list.sort()
            odict  = OrderedDict()

            for score in score_list:
                if score <= max_score:
                    temp_list = conflict.get(score)
                    odict[score] = list(temp_list)

            odict_list.append(odict)

        return odict_list

    #---------------------------------------------------------------------------
    def find_level_slots(self):
        """Find or make matching occurrences for auto scheduler.
        Precedence: 1-try to FIND Level 1 match, if not,
        try to MAKE Level 1 match, if not, find Level 2, so on...
        Differs from manual schedule levels slighty in that
        all levels here require right duration.
        """

        from swingtime.models import Occurrence  #  Avoid circular import

        if self.interest:
            proxy_interest = self.interest
        else:
            proxy_interest = self.get_default_interest()
        if self.is_a_training():
            proxy_interest = abs(6 - proxy_interest)
            # Make high demand classes in low interest timeslots and vice versa
            challenge = None
            training = self
        elif self.is_a_challenge():
            challenge = self
            training = None

        dur_delta = int(float(self.duration) * 60)
        pls = self.possible_locations()

        #base_q is base level requirements:
        # made but empty, right time, right location
        # don't know about interest or conflicts.
        base_q = list(Occurrence.objects.filter(
                challenge=None,
                training=None,
                location__in=pls,
                end_time=F('start_time') + timedelta(minutes=dur_delta)
                ))
        level1find = []
        level1halffind = []  # If interest doesn't quite match but no conflicts
        level2find = []
        level3find = []

        for o in base_q:  # Sort list rather than multiple queries

            if o.interest and (abs(float(o.interest) - float(proxy_interest)) < 1):
            # Need abs, otherwise causes problems w/ apprxiamted decimal interest
                level1find.append(o)
            elif o.interest and (abs(float(o.interest) - float(proxy_interest)) < 2):
                level2find.append(o)
            else:
                level3find.append(o)

        # Still need conflict sort
        for l in [level1find, level2find]:
            for o in l:
                o.challenge = challenge  # Don't save!
                o.training = training  # DON'T SAVE!
                score = 0
                blackout_conflict = o.blackout_conflict()
                if blackout_conflict:
                    this_score = len(blackout_conflict) * 100
                    score += this_score

                figurehead_conflict = o.figurehead_conflict()
                if figurehead_conflict:
                    this_score = len(figurehead_conflict) * 10
                    score += this_score

                participant_conflict = o.participant_conflict()
                if participant_conflict:
                    this_score = len(participant_conflict) * 1
                    score += this_score

                if score > 99:
                    if o in level1find:
                        level1find.remove(o)
                    if o in level2find:
                        level2find.remove(o)
                    level3find.append(o)
                elif score <= 99 and score > 0:
                    if o in level1find:
                        level1find.remove(o)

                    if o not in level2find:
                        level2find.append(o)

                # If there's no conflict but it's still a +/- 1 interest match
                elif score <= 0:
                    if o in level2find:
                        level2find.remove(o)
                    level1halffind.append(o)

                o.challenge = None  # Back to blank
                o.training = None  # Backto blank

        return level1find, level1halffind, level2find, level3find

    #---------------------------------------------------------------------------
    def scheduled(self):
        os = list(self.occurrence_set.all())
        return os

    #---------------------------------------------------------------------------
    def get_activity_type(self):
        """Written so can easily see if is sanctioned game/chal in templates.
        Written so can use cycle template tag for both challenges & trainings.
        """

        loc_str = ""

        # Both have location_type
        if self.location_type == 'EITHER Flat or Banked Track':
            loc_str = "FT or BT "
        elif self.location_type == "Flat Track":
            loc_str = "FT "
        elif self.location_type == 'Banked Track':
            loc_str = "BT "
        elif self.location_type == 'Off Skates Athletic Training':
            loc_str = "Xsk8 Athletic "
        elif self.location_type == 'Seminar/Conference Room':
            loc_str = "Xsk8  "

        if self.is_a_training():
            loc_str += ("(" + self.duration +" Hrs)")

        elif self.is_a_challenge():
            if self.gametype in ['3CHAL', '6CHAL', '36CHAL']:
                if self.gametype == '3CHAL':
                    loc_str += "30m"
                elif self.gametype == '6CHAL':
                    loc_str += "60m"
                elif self.gametype == '36CHAL':
                    loc_str += "30 or 60m"
                loc_str += " Challenge"
            elif self.gametype == "6GAME":
                loc_str += "60m Reg/San Game"

        return loc_str

    #---------------------------------------------------------------------------
    def get_view_url(self):
        if self.is_a_training():
            from scheduler.views import view_training  #  Avoid circular import
            return reverse('scheduler.views.view_training', args=[str(self.pk)])

        elif self.is_a_challenge():
            from scheduler.views import view_challenge  #  Avoid circular import
            return reverse('scheduler.views.view_challenge', args=[str(self.pk)])

    #---------------------------------------------------------------------------
    def get_edit_url(self):
        if self.is_a_training():
            from scheduler.views import edit_training  #  Avoid circular import
            return reverse('scheduler.views.edit_training', args=[str(self.pk)])

        elif self.is_a_challenge():
            #I think this might actually be stupid
            from scheduler.views import edit_challenge
            return reverse('scheduler.views.edit_challenge', args=[str(self.pk)])

    #---------------------------------------------------------------------------
    def get_sched_assist_url(self):
        if self.is_a_training():
            from swingtime.views import sched_assist_tr  #  Avoid circular import
            return reverse('swingtime.views.sched_assist_tr', args=[str(self.pk)])
        elif self.is_a_challenge():
            from swingtime.views import sched_assist_ch  #  Avoid circular import
            return reverse('swingtime.views.sched_assist_ch', args=[str(self.pk)])

    #---------------------------------------------------------------------------
    class Meta:

        abstract = True


#===============================================================================
class ChallengeManager(models.Manager):

    #---------------------------------------------------------------------------
    def submission_full(self, con):
        """If too many challenges submitted for con, returns true. Else, false.
        Excludes Games from count.
        """

        submissions = list(Challenge.objects
                .filter(con=con)
                .exclude(submitted_on=None)
                .exclude(gametype="6GAME")
                )

        if len(submissions) < CLOSE_CHAL_SUB_AT:
            return False
        else:
            return True


#===============================================================================
class Challenge(Activity):

    roster1 = (models.ForeignKey(
            Roster, related_name="roster1", null=True, blank=True,
            on_delete=models.SET_NULL)
            )
    roster2 = (models.ForeignKey(
            Roster, related_name="roster2", null=True, blank=True,
            on_delete=models.SET_NULL)
            )
    # note:
    # Once upon a time I let the same roster be used for multiple
    # challenges, but that ended up confusing everyone.
    # So that's why roster:challenge is essentially a 1:1, but
    # I have to write awkward stuff around it really being fk
    # Should be changed, but don't want to introduce new bugs.
    captain1accepted = models.BooleanField(default=True)
    captain2accepted = models.BooleanField(default=False)
    roster1score = models.IntegerField(null=True, blank=True)
    roster2score = models.IntegerField(null=True, blank=True)
    ruleset = models.CharField(max_length=30, choices=RULESET, default=RULESET[0][0])
    gametype = models.CharField(max_length=250, choices=GAMETYPE, default=GAMETYPE[0][0])
    submitted_on = models.DateTimeField(null=True, blank=True)
    objects = ChallengeManager()

    #---------------------------------------------------------------------------
    def __unicode__(self):

       return "%s: %s"  % (self.name, self.con)

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        string_fields = ['internal_notes','communication']
        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        # Should have made the name a property. This is stupid.
        if self.roster1 and self.roster1.name:
            name1 = self.roster1.name
        else:
            name1 = "?"
        if self.roster2 and self.roster2.name:
            name2 = self.roster2.name
        else:
            name2 = "?"
        self.name = "%s vs %s" % (name1, name2)

        super(Challenge, self).save()

    #---------------------------------------------------------------------------
    def roster4registrant(self, registrant):
        """takes in registrant, returns which team they're on"""

        if registrant in self.roster1.participants.all():
            return roster1
        elif registrant in self.roster2.participants.all():
            return roster2
        else:
            return None

    #---------------------------------------------------------------------------
    def rosterreject(self, roster):
        """takes in roster, rejects challenge.
        If both have rejected, deletes challenge.
        """

        opposing_cap = None
        opposing = None

        if self.roster1 == roster:
            self.captain1accepted = False
            if self.roster2:
                opposing = self.roster2

        elif self.roster2 == roster:
            self.captain2accepted = False
            if self.roster1:
                opposing = self.roster1

        if not self.captain1accepted and not self.captain2accepted:
            for r in [self.roster1, self.roster2]:
                if r :
                    cappy = r.captain
                    # If this is this roster's only challange
                    if len(list(r.roster1.all()) + list(r.roster2.all())) == 1:
                        r.delete()
                    if cappy:
                        cappy.save()  #To reset captain number

            if self.id and self.pk:
                self.delete()
        else:
            # Set rejected roster back to defaults. Gets saved in method.
            roster.restore_defaults()
             # Make sure after naked roster is saved, so chal name will include ? again
            self.save()

    #---------------------------------------------------------------------------
    def my_team_status(self, registrant_list):
        """takes in registrant list, tells you which team registrant is captaining,
        whether registrant has accepted, who opponent is, and if they'e accepted.
        """

        if (self.roster1 and self.roster1.captain and
                (self.roster1.captain in registrant_list)
                ):
            my_team = self.roster1
            opponent = self.roster2
            my_acceptance = self.captain1accepted
            opponent_acceptance = self.captain2accepted
        elif (self.roster2 and self.roster2.captain and
                (self.roster2.captain in registrant_list)
                ):
            my_team = self.roster2
            opponent = self.roster1
            my_acceptance = self.captain2accepted
            opponent_acceptance = self.captain1accepted
        else:
            my_team = None
            opponent = None
            my_acceptance = None
            opponent_acceptance = None

        return my_team, opponent, my_acceptance, opponent_acceptance

    #---------------------------------------------------------------------------
    def can_submit_chlg(self):
        """First checks to see if both captains have accepted.
        If yes and is a Game, can submit as long as first sub date has passed,
        and schedule is not final.
        If yes and is a Challenge, can submit as long as first sub date has
        passed and max chal cap hasn't been reached.
        """

        can_sub = False
        if self.roster1 and self.captain1accepted and self.roster2 and self.captain2accepted:
            if self.con.can_submit_chlg_by_date():
                if self.gametype == "6GAME" and not self.con.sched_final:
                    can_sub = True
                elif self.gametype != "6GAME" and self.con.can_submit_chlg():
                    can_sub = True

        return can_sub

    #---------------------------------------------------------------------------
    def skill_display(self):
        """Like method of same name for Roster, makes it so don't see A0,
        just A, or AB, or something more understandable.
        If different for 2 rosters, returns both. otherwise if same, 1.
        """
        r1skill = r2skill = display = None

        if self.roster1:
            r1skill = self.roster1.skill_display()
        if self.roster2:
            r2skill = self.roster2.skill_display()

        if r1skill and r2skill:
             if r1skill != r2skill:
                 display = "%s & %s" % (r1skill, r2skill)
             else:
                 display = r1skill
        elif r1skill and not r2skill:
            display = r1skill
        elif r2skill and not r1skill:
            display = r2skill

        return display

    #---------------------------------------------------------------------------
    def gender_display(self):
        """Like skill display above but w/ gender."""
        r1gen = r2gen = display = None

        if self.roster1:
            r1gen = self.roster1.gender
        if self.roster2:
            r2gen = self.roster2.gender

        if r1gen and r2gen:
             if r1gen != r2gen:
                 display = "%s & %s" % (r1gen, r2gen)
             else:
                 display = r1gen
        elif r1gen and not r2gen:
            display = r1gen
        elif r2gen and not r1gen:
            display = r2gen

        return display

    #---------------------------------------------------------------------------
    class Meta:
        ordering=('-con__start', 'name')
        unique_together = ('con', 'name', 'roster1', 'roster2')

#-------------------------------------------------------------------------------
pre_save.connect(challenge_defaults, sender=Challenge)
post_save.connect(delete_homeless_chg, sender=Challenge)
pre_delete.connect(delete_homeless_roster_chg, sender=Challenge)


#===============================================================================
class Training(Activity):
    #activity has: name, con, location_type, RCaccepted, created_on, duration
    coach = models.ManyToManyField('Coach', blank=True)
    # coach can't be ForeignKey bc can be multiple coaches
    skill = models.CharField(max_length=30, null=True,blank=True,choices=SKILL_LEVEL_TNG)
    onsk8s = models.BooleanField(default=True)
    contact = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    regcap = models.IntegerField(null=True, blank=True)
    audcap = models.IntegerField(null=True, blank=True)

    sessions = models.IntegerField(default=1, choices=SESSIONS_TR)

    #---------------------------------------------------------------------------
    def __unicode__(self):
       return "%s  (%s)"  % (self.name, self.con)

    #---------------------------------------------------------------------------
    def get_coach_registrants(self):
        """Gets all registrants for Coach,
        (remember Coach is tied to User and not a specific year)
        """

        registrants = []
        for c in self.coach.all():
            try:
                registrants.append(Registrant.objects.get(con=self.con, user=c.user))
            except:
                pass

        return registrants

    #---------------------------------------------------------------------------
    def skills_allowed(self):
        if self.skill:
            allowed = list(self.skill)
            if "O" in allowed:
                allowed.remove("O")
        else:
            allowed = ["A", "B", "C", "D"]

        return allowed

    #---------------------------------------------------------------------------
    def skill_display(self):
        """Makes it so don't see A0, just A, or AB, etc. """
        prettify = ''.join(self.skills_allowed())
        return prettify

    #---------------------------------------------------------------------------
    def skill_tooltip_title(self):

        if self.skill:
            allowed = self.skills_allowed()
            allowed.sort(reverse=True)
            skill_dict=dict(SKILL_LEVEL)
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
            return str_base + str_mid + str_end
        else:
            return "No skill restrictions for registration"

    #---------------------------------------------------------------------------
    def skill_icon(self):
        if not self.skill:
            return "glyphicon icon-universal-access"

    #---------------------------------------------------------------------------
    def intl_icon(self):
        if self.intl:
            return "glyphicon icon-globe-alt"
        else:
            return "glyphicon icon-universal-access"

    #---------------------------------------------------------------------------
    def onsk8s_icon(self):
        if self.onsk8s:
            return "glyphicon icon-onskates"
        else:
            return "glyphicon icon-shoes"

    #---------------------------------------------------------------------------
    def onsk8s_tooltip_title(self):
        if self.onsk8s:
            return "This is an On-Skates Training."
        else:
            return "This is an Off-Skates Training."

    #---------------------------------------------------------------------------
    def passes_allowed(self):
        if self.onsk8s:
            allowed = ['MVP']
        else:
            allowed = ['MVP','Skater','Offskate']

        return allowed

    #---------------------------------------------------------------------------
    def passes_str(self):

        allowed = self.passes_allowed()
        passstr = ""
        for s in allowed:
            passstr += (s + ", ")
        passstr = passstr[:-2]

        return passstr

    #---------------------------------------------------------------------------
    def passes_tooltip_title(self):

        pass_list = self.passes_allowed()
        pass_string = ""
        if len(pass_list) > 1:
            if len(pass_list) > 2:
                for item in pass_list[:-1]:
                    pass_string += item + ", "
            else:
                pass_string += pass_list[0]
            pass_string += " or " + pass_list[-1]
        else:
            pass_string = pass_list[0]

        base_str = self.onsk8s_tooltip_title()

        tooltip_title = (base_str +
                (" Registrant must have %s pass in order to register" % (pass_string))
                )

        return tooltip_title

    #---------------------------------------------------------------------------
    def contact_icon(self):
        if self.contact:
            return "glyphicon icon-helmet"
        else:
            return "glyphicon icon-nocontact"

    #---------------------------------------------------------------------------
    def contact_text(self):
            return "Contact: "

    #---------------------------------------------------------------------------
    def contact_tooltip_title(self):
        if self.contact:
            return "This training includes Contact"
        else:
            return "This training does not include Contact"

    #---------------------------------------------------------------------------
    def full_description(self):
        """Returns training description, then coach description for each coach.
        Or empty quotes.
        """

        des = ""
        if self.description:
            des += self.description
        for c in self.coach.all():
            if c.description:
                des += "\n\n" + c.description

        return des

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        string_fields = ['name', 'description', 'communication']
        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        if self.internal_notes:
            cleaned_notes = ascii_only(self.internal_notes)
            self.internal_notes = cleaned_notes

        if not self.duration:
            if self.onsk8s:
                self.duration = DEFAULT_ONSK8S_DURATION
            else:
                self.duration = DEFAULT_OFFSK8S_DURATION

        super(Training, self).save()

    #---------------------------------------------------------------------------
    class Meta:

        ordering = ('-con__start', 'name')


#===============================================================================
class Coach(models.Model):

    user = models.OneToOneField(
            User, null=True, blank=True, on_delete=models.SET_NULL
            )
    description = models.TextField(null=True, blank=True)
    can_email=models.BooleanField(default=True)

    internal_notes= models.TextField(null=True,blank=True)

    #---------------------------------------------------------------------------
    def __unicode__(self):

        try:
            return "Coach %s" % (self.user.first_name)
        except:
            return self.id

    #---------------------------------------------------------------------------
    class Meta:
        ordering = ('user',)

    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """Removes non-ascii chars from description, internal notes"""

        string_fields = ['description', 'internal_notes']
        for item in string_fields:
            att_unclean = getattr(self, item)
            if att_unclean:
                cleaned_att = ascii_only(att_unclean)
                setattr(self, item, cleaned_att)

        super(Coach, self).save()

    #---------------------------------------------------------------------------
    def email_coach(self, sending_user, message):
        """if coach has agreed to accept emails and has a user and user has an
        email address. By default all registrant should have users and email
        addresses. But who knows, maybe one will get deleted.
        Takes user that wants to email, message, tries to email.
        Returns True if successful.
        """

        email_success = False

        if (self.can_email):
            subject = ("%s, %s has sent you a message through the RollerTron \
                    site!" % (self.user.first_name, sending_user.first_name)
                    )
            message_body = ("Message below. Please respond to %s, not to us.\
                    \n\n\n%s" % (sending_user.email, message)
                    )
            email = EmailMessage(
                    subject=subject,
                    body=message_body,
                    to=[self.user.email],
                    reply_to=[sending_user.email]
                    )
            try:
                email.send(fail_silently=False)
                email_success = True
            except:
                try:
                    send_mail(
                            subject,
                            message_body,
                            from_email=SECOND_CHOICE_EMAIL,
                            recipient_list=[self.user.email],
                            fail_silently=False,
                            auth_user=SECOND_CHOICE_EMAIL,
                            auth_password=SECOND_CHOICE_PW
                            )
                    email_success = True
                except:
                    email_success = False

        return email_success

    #---------------------------------------------------------------------------
    def get_absolute_url(self):

        from scheduler.views import view_coach

        return reverse('scheduler.views.view_coach', args=[str(self.pk)])

    #---------------------------------------------------------------------------
    def get_my_schedule_url(self):
        """Used for bosses to check coach's schedule"""

        from con_event.monkey_patching import get_my_schedule_url

        return self.user.get_my_schedule_url()
