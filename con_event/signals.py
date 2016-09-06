from django.db.models import Q
from django.forms.models import model_to_dict

from rcreg_project.extras import remove_punct, ascii_only, ascii_only_no_punct
from rcreg_project.settings import BIG_BOSS_GROUP_NAME, LOWER_BOSS_GROUP_NAME


def update_user_fl_name(sender, instance, **kwargs):
    """post_save signal from Registrant.
    Syncs user first and last name w/ registrant sk8 name and sk8#,
    or first and last name, if sk8 name / # unavailable.
    """

    if instance.user:
        # This is hypothetical-- every Registrant should have a User.
        user = instance.user  # To shorten these long lines
        reg = instance  # To shorten these long lines

        if (reg.sk8name and reg.sk8number):
            user.first_name, user.last_name = reg.sk8name, reg.sk8number
            user.save()

        elif (reg.first_name and reg.last_name):
            user.first_name, user.last_name = reg.first_name, reg.last_name
            user.save()


def delete_homeless_user(sender, instance, **kwargs):
    '''pre_delete from Registrant.
    If this is the only registrant for its user, user is also deleted.
    Unless user is Staff. Staff & Superusers can exist without registrants.
    '''

    if instance.user:
        # This is hypothetical-- every Registrant should have a User.
        user = instance.user  # To shorten these long lines
        reg = instance  # To shorten these long lines

        if user.registrants() and len(user.registrants()) <= 1:
            if (not user.is_staff and not user.is_superuser):
                user.delete()


def clean_registrant_import(sender, instance, **kwargs):
    """pre_save from Registrant. Vestigial, but no reason to delete.
    If import/export app is used to import registrants, this will clean data.
    Since RollerCon staff can import registrants via the 'upload_reg' view,
    this is outdated, but kept just in case someone uses import/export upload.
    """

    model_dict = model_to_dict(instance)

    for k, v in model_dict.iteritems():
        if k in [
                'BPT_Ticket_ID', 'pass_type', 'last_name', 'first_name',
                'email', 'sk8name', 'sk8number', 'affiliation', 'volunteer',
                'favorite_part', 'ins_carrier', 'ins_number', 'age_group',
                'skill', 'gender']:
            #  This is the next line after 'if k in ...' really long list.
            value = getattr(instance, k)
            clean_value = ascii_only(value)
            if clean_value and len(clean_value) > 100:
                clean_value = clean_value[:100]
            setattr(instance, k, clean_value)

    # Just in case the Excel sheet is inconsistent with terminology re: passes
    pass_split = str(instance.pass_type).upper().split()
    nopass = ["NOT", "SKATING", "NA", "N/A", "NONE", "0", "OFF", "OFFSKATE"]
    sk8erpwords = ["SKATER", "SK8ER", "ON SK8S", "SK8S"]

    if set(nopass).intersection(pass_split):
        instance.pass_type = "Offskate"
    elif set(sk8erpwords).intersection(pass_split):
        instance.pass_type = "Skater"
    else:
        instance.pass_type = "MVP"  # err on the side of giving better pass.

    # Just in case the Excel sheet is inconsistent with terminology re: skill
    skill_split = str(instance.skill).upper().split()

    if set(["ADVANCED", "A"]).intersection(skill_split):
        instance.skill = "A"
    elif set(["INTERMEDIATE", "B"]).intersection(skill_split):
        instance.skill = "B"
    elif set(["BEGINNER", "C"]).intersection(skill_split):
        instance.skill = "C"
    elif set(["ROOKIE", "D"]).intersection(skill_split):
        instance.skill = "D"
    else:
        instance.skill = None

    # Just in case the Excel sheet is inconsistent with terminology re: gender
    gender_split = str(instance.gender).upper().split()

    if set(["F", "FEMALE"]).intersection(gender_split):
        instance.gender = "Female"
    elif set(["M", "MALE"]).intersection(gender_split):
        instance.gender = "Male"
    else:
        instance.gender = "NA/Coed"


def match_user(sender, instance, **kwargs):
    """pre_save signal from Registrant.
    Looks for user w/ registrant email as user email or username.
    If > 1 user-- which should not happen-- uses most recently created.
    If no match, makes new user with a random password.
    """

    from django.contrib.auth.models import User  # Avoid circular import

    if instance.email and not instance.user:
        try:
            # There should only be one User w/ email; should be unique.
            # In case of 2, get most recent User w/ same email.
            user_q = list(
                        user.objects.filter(
                            Q(username=instance.email) |
                            Q(email=instance.email)).
                        latest('id')
                        )
            user = user_q[0]
            created = False
        except:  # Create new User, no match with Registrant email.
            user, created = User.objects.get_or_create(username=instance.email)

        if created:
            password = User.objects.make_random_password()
            user.set_password(password)

            if instance.sk8name:
                user.first_name = instance.sk8name
                if instance.sk8number:
                    user.last_name = instance.sk8number
                else:
                    user.last_name = "X"

            elif instance.first_name and instance.last_name:
                user.first_name = instance.first_name
                user.last_name = instance.last_name

            user.email = instance.email
            user.save()

        # If created over. This runs as long as there was an email and no User.
        instance.user = user
        instance.save()


def sync_reg_permissions(sender, instance, **kwargs):
    """post_save from Registrant.
    If user is in custom BIG_BOSS_GROUP_NAME or LOWER_BOSS_GROUP_NAME groups,
    gives staff / superuser permissions.
    Does not work backwards--
    one can be a staff/superuser without being in a custom group.
    In case permissions are given piecemeal.
    """
    
    user = instance.user
    groups = user.groups.values_list('name',flat=True)

    if (BIG_BOSS_GROUP_NAME in groups) or (LOWER_BOSS_GROUP_NAME in groups):

        if not user.is_staff:  # Either of these groups makes you staff.
            user.is_staff = True
            user.save()
        if BIG_BOSS_GROUP_NAME in groups:  # Must be Big Boss to get Superuser.
            if not user.is_superuser:
                user.is_superuser = True
                user.save()
