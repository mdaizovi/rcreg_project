#con_event.forms
from django import forms
from django.forms import ModelForm
from con_event.models import Con, Registrant,Blackout,SKILL_LEVEL_SK8R
#from datetimewidget.widgets import DateTimeWidget #really beautiful widget I intended to use for Blackots, ended up just splitting it into am/pm
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
import string
import re


class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['search_q']=forms.CharField(required=False,label="Search")
        self.tooltip="To refine selection, search by skater name. Otherwise, select from all eligible skaters"

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

    def normalize_query(self, findterms=re.compile(r'"([^"]+)"|(\S+)').findall,normspace=re.compile(r'\s{2,}').sub):
        ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
        from http://julienphalip.com/post/2825034077/adding-search-to-a-django-site-in-a-snap
        '''
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(self['search_q'].value())]

    def get_query(self, search_fields):
        ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
        from http://julienphalip.com/post/2825034077/adding-search-to-a-django-site-in-a-snap
        '''
        query = None # Query to search for every search term
        terms = self.normalize_query()
        for term in terms:
            or_query = None # Query to search for a given term in each field
            for field_name in search_fields:
                q = Q(**{"%s__icontains" % field_name: term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q
            if query is None:
                query = or_query
            else:
                query = query & or_query
        return query


class RegistrantProfileForm(ModelForm):
    """Used in registrant_profile view"""
    def __init__(self, *args, **kwargs):
        super(RegistrantProfileForm, self).__init__(*args, **kwargs)
        instancepk=self.instance.id
        self.fields["skill"]=forms.CharField(widget=forms.Select(choices=SKILL_LEVEL_SK8R), label='Skill Level')

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'id': '%s_for_%s'%(str(field),str(instancepk)),
                'name': '%s_for_%s'%(str(field),str(instancepk)),
                })
        #so beautiful! http://django-datetime-widget.asaglimbeni.me/model_form_v3/
        #self.fields["availability_start"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_start"}, usel10n = True, bootstrap_version=3),label ="OPTIONAL")
        # self.fields["availability_start"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_start"}, usel10n = True, bootstrap_version=3),required=False,label="Availability Start*")
        # self.fields["availability_end"]=forms.DateTimeField(widget=DateTimeWidget(attrs={'id':"availability_end"}, usel10n = True, bootstrap_version=3),required=False,label="Availability End*")
        self.fields['sk8name'].widget.attrs['disabled'] = True #only looks disabled, I can still change it?
        self.fields['sk8name'].required = False
        self.fields['sk8number'].required = False
        self.fields['intl'].widget.attrs['disabled'] = True #only looks disabled, I can still change it?
        self.fields['pass_type'].widget.attrs['disabled'] = True #only looks disabled, I can still change it?
        self.fields['intl'].required = False
        self.fields['pass_type'].required = False

    class Meta:
        model = Registrant
        fields = ['sk8name','sk8number','skill','gender','pass_type','intl']
        labels = {
            'sk8name': _('Skate Name'),
            'sk8number': _('Skate Number'),
            'intl': _('International'),
            'pass_type': _("Pass Type"),
        }

class EligibleRegistrantForm(forms.Form):
    """Used all over the place for editing Roster participants and TrainingRoster participants."""
    def __init__(self, *args, **kwargs):
        #vague so can do custom filtering each time form is used. ex, right pass level, skill level, etc.
        eligibles = kwargs.pop('my_arg')

        super(EligibleRegistrantForm, self).__init__(*args, **kwargs)
        if eligibles:
            ELIGIBLE_REGISTRANTS=[]
            for item in eligibles:
                if item.sk8name and item.sk8number:
                    ELIGIBLE_REGISTRANTS.append((item.pk, (item.sk8name+" "+item.sk8number)))
                elif item.sk8name:
                    ELIGIBLE_REGISTRANTS.append((item.pk, (item.sk8name)))
                elif item.first_name and item.last_name:
                    ELIGIBLE_REGISTRANTS.append((item.pk, (item.first_name+" "+item.last_name)))
                elif item.first_name:
                    ELIGIBLE_REGISTRANTS.append((item.pk, (item.first_name)))

        else:
            ELIGIBLE_REGISTRANTS=[((None),("None"))]

        self.fields['eligible_registrant']=forms.CharField(required=True,label="Skaters",
            widget=forms.Select(choices=ELIGIBLE_REGISTRANTS))

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })

class ConSchedStatusForm(ModelForm):
    """Used in Calendar for Khaleesi, so she doesn't have to go to Admin."""
    class Meta:
        model = Con
        fields = ['sched_visible','sched_final']
        labels = {
            'sched_visible': _('Schedule Visible'),
            'sched_final': _('Schedule Final'),
        }

    def __init__(self, *args, **kwargs):
        super(ConSchedStatusForm, self).__init__(*args, **kwargs)

        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                })


class AvailabilityForm(forms.Form):
    """Used to get Blackouts from Captains and Coaches for scheduling purposes.
    Shows up in My Profile, if they're coaching or captining."""

    def __init__(self, *args, **kwargs):
        date = kwargs.pop('date')
        super(AvailabilityForm, self).__init__(*args, **kwargs)

        self.fields["date"] = forms.DateField(required=True,label="Date:",initial=date.strftime("%a %B %d, %Y"))
        self.fields["am"] = forms.BooleanField(label='Available AM', initial=True)
        self.fields["pm"] = forms.BooleanField(label='Available PM', initial=True)


        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                 'id': str(date),
                 'name': str(date),
                })

        self.fields['date'].widget.attrs['disabled'] = True
        self.fields['am'].required = False
        self.fields['pm'].required = False
