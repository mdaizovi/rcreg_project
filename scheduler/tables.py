from scheduler.models import Coach,Roster, Challenge, Training,DEFAULT_ONSK8S_DURATION, DEFAULT_OFFSK8S_DURATION,DEFAULT_CHALLENGE_DURATION, DEFAULT_SANCTIONED_DURATION,GAMETYPE

import django_tables2 as tables
import itertools
from django.utils.safestring import mark_safe
from django.utils.html import escape
from scheduler.forms import ChalStatusForm,TrainStatusForm
from django_tables2.utils import A # alias for Accessor
from django.core.urlresolvers import reverse

class ChallengeTable(tables.Table):
    name = tables.Column(verbose_name="Name",attrs={"td": {"style": "max-width:150px"}})
    gametype = tables.Column(verbose_name="Game Type",attrs={"td": {"style": "max-width:150px"}})
    location_type = tables.Column(verbose_name="Location Type",attrs={"td": {"style": "max-width:40px"}})
    duration = tables.Column(verbose_name="Duration",attrs={"td": {"style": "max-width:40px"}})
    submitted_on = tables.Column(verbose_name="Submitted on",attrs={"td": {"style": "max-width:40px"}})
    status = tables.Column(verbose_name="Status",attrs={"td": {"style": "max-width:75px","colspan": "5"}},orderable=False)

    def render_name(self,value):
        url=value.get_view_url()
        name=value.name
        pk=value.pk
        string="<a href='%s'>%s</a>" % (url,name)
        return mark_safe(string)


    def render_status(self, value):
        return value

    def render_submitted_on(self, value):
        if value:
            return value.strftime("%x %H:%M")

    class Meta:
        model = Challenge
        fields=("name","gametype","location_type","duration","submitted_on","status")
        attrs = {"class": "table table-striped"}
