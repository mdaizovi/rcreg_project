from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator


NEW_USERNAME_LENGTH = 100


def monkey_patch_username():
    """Allows the username to be 100 chars, instead of just 30
    for long emails, since email address is username."""

    username = User._meta.get_field("username")
    username.max_length = NEW_USERNAME_LENGTH
    for v in username.validators:
        if isinstance(v, MaxLengthValidator):
            v.limit_value = NEW_USERNAME_LENGTH

monkey_patch_username()
