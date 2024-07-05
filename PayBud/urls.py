"""PayBud URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from PayBudApp import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("payment/bill/", views.Bill.as_view(), name = "Bill another user"), #add names

    path("payment/account/login/", views.Login.as_view(), name = "Authenticate with PayBud"),
    path("payment/account/logout/", views.Logout.as_view(), name = "Logout of PayBud"),
    path("payment/account/deposit/", views.Deposit.as_view(), name = "Deposit money into an account"),
    path("payment/account/balance/", views.GetBalance.as_view(), name = "Check an account's balance"),
    path("payment/account/exists/", views.Exists.as_view(), name = "Check if an account exists"),
    path("payment/account/details/", views.GetDetails.as_view(), name = "Check the details of an account"),

    path("payment/outbound/create/", views.CreateOutbound.as_view(), name = "Create an outbound payment record"),
    path("payment/outbound/allow/", views.AllowOutbound.as_view(), name = "Allow a payment to be made"),
    path("payment/outbound/transfer/", views.TransferOutbound.as_view(), name = "Transfer money from one account to another"),   
    path("payment/outbound/redeem/", views.RedeemOutbound.as_view(), name = "Internal endpoint used to aid a money transfer"), 
    path("payment/outbound/fetch/", views.FetchOutbound.as_view(), name = "Get the details of an outbound payment record"), 
]
