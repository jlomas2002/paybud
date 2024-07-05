from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Account


class UserAccountCreationForm(UserCreationForm):
    class Meta:
        model = Account
        fields = ('email',)


class UserAccountChangeForm(UserChangeForm):
    class Meta:
        model = Account
        fields = ('email',)
