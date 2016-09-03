from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from monkey_patch.models import NEW_USERNAME_LENGTH


UserChangeForm.base_fields['username'].max_length = NEW_USERNAME_LENGTH
UserChangeForm.base_fields['username'].widget.attrs['maxlength'] = (
                                                            NEW_USERNAME_LENGTH
                                                            )
UserChangeForm.base_fields['username'].validators[0].limit_value = (
                                                            NEW_USERNAME_LENGTH
                                                            )
UserChangeForm.base_fields['username'].help_text = (
                    UserChangeForm.base_fields['username'].help_text.replace(
                    '30', str(NEW_USERNAME_LENGTH))
                    )

UserCreationForm.base_fields['username'].max_length=NEW_USERNAME_LENGTH

UserCreationForm.base_fields['username'].widget.attrs['maxlength']=(
                                                            NEW_USERNAME_LENGTH
                                                            )
UserCreationForm.base_fields['username'].validators[0].limit_value=(
                                                            NEW_USERNAME_LENGTH
                                                            )

UserCreationForm.base_fields['username'].help_text=(
    UserChangeForm.base_fields['username'].help_text.replace('30', str(NEW_USERNAME_LENGTH)))
