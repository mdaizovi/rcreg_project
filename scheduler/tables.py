import itertools

from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.html import escape

import django_tables2 as tables
from django_tables2.utils import A  # alias for Accessor
from scheduler.app_settings import (DEFAULT_ONSK8S_DURATION,
        DEFAULT_OFFSK8S_DURATION, DEFAULT_CHALLENGE_DURATION,
        DEFAULT_SANCTIONED_DURATION
        )
from scheduler.forms import (
        ChalStatusForm, TrainStatusForm, CInterestForm, TInterestForm
        )
from scheduler.models import Coach, Roster, Challenge, Training, GAMETYPE


"""All of these tables create a sortable table from Model objects.
Mostly, if not exclusively, used in Khaleesi section of swingtime scheduling.
"""

#===============================================================================
class RosterTable(tables.Table):
    #  Not actual model fields, just used for styling consistency within table
    sm_fixed = {"style": "width:40px;"}
    med_minmax = {"style": "min-width:50px; max-width:100px;"}
    lg_minmax = {"style": "min-width:75px; max-width:150px;"}

    #  Begin the table fields
    sk8name = tables.Column(verbose_name="Name")
    sk8number = tables.Column(verbose_name="Number")

    #---------------------------------------------------------------------------
    class Meta:

        model = Roster
        fields = ("sk8name", "sk8number")
        attrs = {"class": "table table-striped"}


#===============================================================================
class ChallengeTable(tables.Table):
    #  Not actual table fields, just used for styling consistency within table
    sm_fixed = {"style": "width:40px;"}
    med_minmax = {"style": "min-width:50px; max-width:100px;"}
    lg_minmax = {"style": "min-width:75px; max-width:150px;"}

    #  Begin the table fields
    name = (tables.Column(
            verbose_name="Name",
            attrs={"td":med_minmax, "th":med_minmax})
            )
    gametype = (tables.Column(
            verbose_name="Game Type",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    location_type = (tables.Column(
            verbose_name="Location Type",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    duration = (tables.Column(
            verbose_name="Duration",
            attrs={"td": sm_fixed, "tr": sm_fixed})
            )
    submitted_on = (tables.Column(
            verbose_name="Submitted on",
            attrs={"td": med_minmax, "tr": med_minmax,})
            )
    interest = (tables.Column(
            verbose_name="Interest",
            attrs={"td": sm_fixed, "th":sm_fixed})
            )
    status = (tables.Column(
            verbose_name="Status",
            attrs={
                    "td": {"style": "min-width:85px;"},
                    "th": {"colspan": "4",
                            "style": "text-align:center; min-width:85px;"
                            }
                    },
            orderable=False)
            )

    #---------------------------------------------------------------------------
    def render_name(self,value):

        url = value.get_view_url()
        name = value.name
        pk = value.pk
        string = "<a href='%s'>%s</a>" % (url, name)

        return mark_safe(string)

    #---------------------------------------------------------------------------
    def render_status(self, value):

        return value

    #---------------------------------------------------------------------------
    def render_submitted_on(self, value):

        if value:

            return value.strftime("%x %H:%M")

    #---------------------------------------------------------------------------
    class Meta:

        model = Challenge
        fields = ("name", "gametype", "location_type", "duration",
                "submitted_on", "interest", "status"
                )
        attrs = {"class": "table table-striped"}


#===============================================================================
class TrainingTable(tables.Table):
    #  Not actual model fields, just used for styling consistency within table
    sm_fixed = {"style": "width:40px;"}
    med_minmax = {"style": "min-width:50px; max-width:100px;"}

    #  Begin the table fields
    name = (tables.Column(
            verbose_name="Name",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    coach = (tables.Column(
            verbose_name="Coach",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    skill = (tables.Column(
            verbose_name="Skill",
            attrs={"td": {"style": sm_fixed}, "th": sm_fixed})
            )
    onsk8s = (tables.BooleanColumn(
            verbose_name="On Sk8s",
            attrs={"td": sm_fixed, "th": sm_fixed})
            )
    contact = (tables.BooleanColumn(
            verbose_name="Contact",
            attrs={"td": sm_fixed, "th": sm_fixed})
            )
    location_type = (tables.Column(verbose_name="Location Type",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    duration = (tables.Column(
            verbose_name="Duration",
            attrs={"td": sm_fixed, "th": sm_fixed})
            )
    created_on = (tables.Column(
            verbose_name="Created on",
            attrs={"td": med_minmax, "th": med_minmax})
            )
    interest = (tables.Column(
            verbose_name="Interest",
            attrs={"td": sm_fixed, "th":sm_fixed})
            )
    status = (tables.Column(
            verbose_name="Status",
            attrs={
                    "td": {"style": "min-width:75px;"},
                    "th": {"colspan": "4",
                            "style": "text-align:center; min-width:75px;"}
                    },
            orderable=False)
            )

    #---------------------------------------------------------------------------
    def render_name(self,value):

        url = value.get_view_url()
        name = value.name
        pk = value.pk
        string = "<a href='%s'>%s</a>" % (url, name)

        return mark_safe(string)

    #---------------------------------------------------------------------------
    def render_status(self, value):

        return value

    #---------------------------------------------------------------------------
    def render_created_on(self, value):

        if value:

            return value.strftime("%x %H:%M")

    #---------------------------------------------------------------------------
    class Meta:

        model = Challenge
        fields = ("name", "coach", "skill", "onsk8s", "contact",
                "location_type", "duration", "created_on", "interest", "status"
                )
        attrs = {"class": "table table-striped"}
