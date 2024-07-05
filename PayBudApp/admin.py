from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .userForms import UserAccountCreationForm, UserAccountChangeForm
from .models import Account, OutboundPayment


class UserAccountAdmin(UserAdmin):
    add_form = UserAccountCreationForm
    form = UserAccountChangeForm

    model = Account

    list_display = ('email', 'balance', 'is_staff', 'is_superuser', 'last_login',)
    list_filter = ('is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff')}
         ),
    )
    search_fields = ('email',)
    ordering = ('email',)

class UserAccountAdmin(UserAdmin):
    add_form = UserAccountCreationForm
    form = UserAccountChangeForm

    model = Account

    list_display = ('email', 'balance', 'is_staff', 'is_superuser', 'last_login',)
    list_filter = ('is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff')}
         ),
    )
    search_fields = ('email',)
    ordering = ('email',)


admin.site.register(Account, UserAccountAdmin)
admin.site.register(OutboundPayment)