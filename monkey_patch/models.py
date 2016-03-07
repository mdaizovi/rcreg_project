from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator

#reference: http://stackoverflow.com/questions/2610088/can-djangos-auth-user-username-be-varchar75-how-could-that-be-done

NEW_USERNAME_LENGTH = 100

def monkey_patch_username():
    username = User._meta.get_field("username")
    username.max_length = NEW_USERNAME_LENGTH
    for v in username.validators:
        if isinstance(v, MaxLengthValidator):
            v.limit_value = NEW_USERNAME_LENGTH

monkey_patch_username()
