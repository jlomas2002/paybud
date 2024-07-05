from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from PayBudApp import accountManager

# Create your models here.
class Account(AbstractBaseUser, PermissionsMixin):
    accountNum = models.AutoField(primary_key=True)
    paymentServiceId = models.IntegerField()
    email = models.EmailField(unique=True)
    balance = models.FloatField()
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'

    objects = accountManager.AccountManager()

class OutboundPayment(models.Model):
    outboundPaymentId = models.AutoField(primary_key=True)
    fromAccountNum = models.ForeignKey(Account, on_delete=models.CASCADE)
    fromPaymentServiceId = models.IntegerField()
    toAccountNum = models.IntegerField()
    toPaymentServiceId = models.IntegerField()
    amount = models.FloatField()
    allowed = models.DateTimeField(default=None, null=True)
    transferred = models.BooleanField(default=False)
