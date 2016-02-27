from django.db.models import Q
from rcreg_project.settings import BIG_BOSS_GROUP_NAME,LOWER_BOSS_GROUP_NAME
from django.forms.models import model_to_dict
from rcreg_project.extras import remove_punct,ascii_only,ascii_only_no_punct
#from django.contrib.auth.models import User#maybe unnecessary?

#http://stackoverflow.com/questions/32287975/django-auto-create-intermediate-model-instances-for-new-instance-created-in-fore
#http://stackoverflow.com/questions/17645801/when-to-use-pre-save-save-post-save-in-django


def update_user_fl_name(sender, instance,**kwargs):
    """postsave signal from Registrant, changes User first and last name if Registrant did.
    This won't show up on sidebar until they go to a new page, but I think that's okay, don't feel like refreshing context"""
    if instance.user:#this should always be true, but just in case
        print "running update_user_fl_name"

        print "instance is ",instance

        print "sk8name", instance.sk8name
        print "sk8name", instance.sk8number
        print "instance.first_name",instance.first_name
        print "instance.last_name",instance.last_name

        print "user is ",instance.user

        print "instance.user.first_name",instance.user.first_name
        print "instance.user.last_name",instance.user.last_name

        if (instance.sk8name and instance.sk8number):
            if((instance.user.first_name !=instance.sk8name) or (instance.user.last_name !=instance.sk8number)):
                print "first part true"
                if instance.user.first_name !=instance.sk8name:
                    instance.user.first_name =instance.sk8name
                if instance.user.last_name !=instance.sk8number:
                    instance.user.last_name =instance.sk8number
                instance.user.save()
        elif (instance.first_name and instance.last_name):
            if ((instance.user.first_name !=instance.first_name) or (instance.user.last_name !=instance.last_name )):
                print "scond part true"
                if instance.user.first_name !=instance.first_name:
                    instance.user.first_name =instance.first_name
                if instance.user.last_name !=instance.last_name:
                    instance.user.last_name =instance.last_name
                instance.user.save()


def delete_homeless_user(sender, instance,**kwargs):
    '''before deleting a registrant, removes user if deleting reg will mean user no longer has any registrants.
    This should not delete users that no longr have registrants.
    REMEMBER never delete all homeless Users, because that will delete SuperUser RollerTron'''
    if instance.user:#this should always be true, but just in case
        if len(instance.user.registrant_set.all()) <= 1:
            instance.user.delete()

def clean_registrant_import(sender, instance,**kwargs):
    """hard-coding of expected format of importing an excel sheet of Registrant data from BPT, and saving it in a format that suits my models
    Fields that I haven't cleaned because I think are fine as-is: email, first_name,last_name,sk8name,sk8number"""

    #attrs = dir(instance)
    #print "attrs",attrs
    #print "instance.__dict__",instance.__dict__
    model_dict=model_to_dict(instance)
    for k,v in model_dict.iteritems():
        if k in ['BPT_Ticket_ID','pass_type','last_name','first_name','email','sk8name','sk8number','skill','gender','affiliation','ins_carrier','ins_number','age_group','volunteer','favorite_part']:
            value = getattr(instance, k)
            clean_value=ascii_only(value)
            if clean_value and len(clean_value)>100:
                clean_value=clean_value[:100]
            setattr(instance, k, clean_value)

    print instance.sk8name,instance.first_name, instance.last_name,instance.email
    pass_split=str(instance.pass_type).split()
    #print "pass_split",pass_split
    if set(["Not","Skating","NA","na","N/A",None,0,"0","Off","Offskate"]).intersection(pass_split):
        instance.pass_type ="Offskate"
    elif set(["Skater","SKATER","Sk8er","On SK8s","SK8s"]).intersection(pass_split):
        instance.pass_type ="Skater"
    else:
        instance.pass_type ="MVP"
    #print "instance.pass_type",instance.pass_type

    skill_split=str(instance.skill).split()
    #print "skill_split",skill_split
    if set(["Advanced","ADVANCED", "advanced","A"]).intersection(skill_split):
        instance.skill ="A"
    elif set(["Beginner","BEGINNER","beginner","C"]).intersection(skill_split):
        instance.skill ="C"
    elif set(["Intermediate","INTERMEDIATE" ,"intermediate","B"] ).intersection(skill_split):
        instance.skill ="B"
    elif set(["Rookie","ROOKIE", "rookie","D"]).intersection(skill_split):
        instance.skill ="D"
    else:
        instance.skill = None
    #print "instance.skill",instance.skill

    gender_split=str(instance.gender).split()
    #print "gender_split",gender_split
    if set(["Female","FEMALE","female"]).intersection(gender_split):
        instance.gender='Female'
    elif set(["Male","MALE","male"]).intersection(gender_split):
        instance.gender='Male'
    else:
        instance.gender='NA/Coed'
    #print "instance.gender",instance.gender


def match_user(sender, instance,**kwargs):
    '''after saving Registrant, looks for User w/ reg email address as User email or username. If>1, uses most recent.
    If no match, makes one.'''
    from django.contrib.auth.models import User

    if not instance.user:
        if instance.email:#this should always be true, but just in case
            try:#Ideally there should only be one that suits this. if not, get most recent w/ same email
                user_query=list(User.objects.filter(Q(username=instance.email)|Q(email=instance.email)).latest('id'))
                user=user_query[0]
                created=False
            except:
                user, created= User.objects.get_or_create(username=instance.email)

        if created:
            password = User.objects.make_random_password()
            user.set_password(password)

            if instance.sk8name:
                user.first_name=instance.sk8name
                if instance.sk8number:
                    user.last_name=instance.sk8number
                else:
                    user.last_name="X"
            elif instance.first_name and instance.last_name:
                user.first_name=instance.first_name
                user.last_name=instance.last_name
            user.email=instance.email
            user.save()
        instance.user=user
        instance.save()


def sync_reg_permissions(sender, instance,**kwargs):
    """Checks to see if user is in custom BIG_BOSS_GROUP_NAME/LOWER_BOSS_GROUP_NAME permission groups,
    if so, gives staff/superuser permissions. If have permissions but not in groups, removes permissions."""

    user=instance.user
    groups=user.groups.all()

    if (BIG_BOSS_GROUP_NAME in groups) or (LOWER_BOSS_GROUP_NAME in groups):
        if not user.is_staff:
            user.is_staff=True
            user.save()
        if BIG_BOSS_GROUP_NAME in groups:
            if not user.is_superuser:
                user.is_superuser=True
                user.save()

    elif user.is_staff or user.is_superuser:#clean out people who are no longer in group
        if user.is_superuser and BIG_BOSS_GROUP_NAME not in groups:
            user.is_superuser=False
            user.save()
        elif user.is_staff and (LOWER_BOSS_GROUP_NAME not in groups) and (BIG_BOSS_GROUP_NAME not in groups):
            user.is_staff=False
            user.save()
