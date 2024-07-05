from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from .models import Account, OutboundPayment
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Q
import requests, json
from datetime import timedelta
from django.utils import timezone
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature
import json
from decouple import config

private_key_pem = config("private_key_pem")

def errorChecker(bodyLength=0, paramLength=0, body=None, queryParams=None, requiredBodyParams=None, requiredQueryParams=None):
    error = ""
    if len(body) != bodyLength:
        error += f"You must provide {bodyLength} params in the request body. Currently, you provide {len(body)}."

    if len(queryParams) != paramLength:
            error += f"You must provide {paramLength} params via a query paramater in the URL. Currently, you provide {len(queryParams)}."

    if error != "":
        return error

    if bodyLength > 0:
        for param in requiredBodyParams:
            if param not in body:
                error = "At least one of the required parameters could not be found in the request body."
                error += "The parameters that must be provided are: "
                for p in requiredBodyParams:
                    error += "\"" + p + "\", "
                error += "."
                return error

    if  paramLength > 0:
        for param in requiredQueryParams:
            if param not in queryParams:
                error = "At least one of the required parameters could not be found in the query parameters."
                error += "The parameters that must be provided are: "
                for p in requiredQueryParams:
                    error += "\"" + p + "\", "
                error += "."
                return error

    return error


def createOutboundFunc(from_accountNum, from_serviceId, to_accountNum, to_serviceId, amount):
    if from_accountNum == to_accountNum and from_serviceId == to_serviceId:
        error = "The inbound and outbound accounts provided are the same."
        return (1, error)

    if not isinstance(from_accountNum, int) or not isinstance(from_serviceId, int) or not isinstance(to_serviceId, int) or not isinstance(to_accountNum, int):
        error = "You must provide all account numbers and payment service IDs as integers."
        return (1, error)

    if not isinstance(amount, int) and not isinstance(amount, float):
        error = "You must provide the amount as an integer or a float."
        return (1, error)

    if amount <= 0:
        error = "You must provide an amount that is greater than zero."
        return (1, error)

    if to_serviceId == 30:
        response = existsFunc(from_accountNum)
        if response[0] != 0:
            return (1, error)

    else:
        directoryResponse = requests.get("https://sc19hwam.eu.pythonanywhere.com/directory/payment-services/lookup/?paymentServiceId="+str(to_serviceId))
        if directoryResponse.status_code != 200:
            error = "Error when attempting web directory lookup. The following error was given: "
            error += directoryResponse.json()["error"]
            return (1, error)

        hostname = directoryResponse.json()["paymentService"]["hostname"]
        #hostname = "http://127.0.0.1:8000"
        response = requests.get("https://" + hostname + "/payment/account/exists/?accountNumber="+str(to_accountNum))
        if response.status_code != 200:
            error = "Error when attempting to create an outbound payment. The following error was given: "
            error += response.json()["error"]
            return (1, error)

        if response.json()["exists"] != True:
            error = "The account specified to transfer money to does not exists."
            return (1, error)

    fromAccount = Account.objects.filter(Q(accountNum=from_accountNum) & Q(paymentServiceId=from_serviceId)).first()
    if not fromAccount:
        error = "The account specified as the outbound payer could not be found."
        return (1, error)

    outboundPayment = OutboundPayment(fromAccountNum=fromAccount, fromPaymentServiceId=from_serviceId, toAccountNum=to_accountNum, toPaymentServiceId=to_serviceId, amount=amount)
    outboundPayment.save()
    return (0, outboundPayment.outboundPaymentId)

def existsFunc(accountNum):
    accountNum = int(accountNum)
    account = Account.objects.filter(Q(accountNum = accountNum)).first()
    if not account:
        error = "An account with this account number could not be found."
        return (False, error)

    return (True, "")

def redeemFunc(paymentServiceId, signature, outboundId):
    if not isinstance(paymentServiceId, int) or not isinstance(outboundId, int):
        error = "You must provide the inbound payment service ID and the outbound payment ID as integers."
        return (1, error)

    directoryResponse = requests.get("https://sc19hwam.eu.pythonanywhere.com/directory/payment-services/lookup/?paymentServiceId="+str(paymentServiceId))
    if directoryResponse.status_code != 200:
        error = "Error when attempting web directory lookup. The following error was given: "
        error += directoryResponse.json()["error"]
        return (1, error)

    public_key_pem = directoryResponse.json()["paymentService"]["publicKey"].replace('\\n', '\n')
    publicKey = serialization.load_pem_public_key(str(public_key_pem).encode('utf-8'))

    try:
        publicKey.verify(signature, str(outboundId).encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        error = "The signature of the destination bank provided is invalid."
        return (1, error)

    payment = OutboundPayment.objects.filter(Q(outboundPaymentId=outboundId)).first()
    if not payment:
        error = "An outbound payment with the provided ID could not be found."
        return (1, error)

    expiry = payment.allowed

    if payment.toPaymentServiceId != paymentServiceId:
        error = "The inbound payment service does not match the provided payment service"

    if expiry == None:
        error = "This payment transfer has not been allowed by the outbound payer."
        return (1, error)

    if expiry < timezone.now():
        error = "This payment transfer could not be allowed as it has expired."
        return (1, error)

    if payment.transferred == True:
        error = "This payment transfer could not be allowed as it has already been transferred."
        return (1, error)

    account = Account.objects.filter(Q(accountNum=payment.fromAccountNum.accountNum)).first()
    if not account:
        error = "An account with this account number could not be found."
        return (1, error)

    if account.balance < payment.amount:
        error = "There are insuffuicient funds to complete this money transfer."
        return (1, error)

    account.balance -= payment.amount
    account.save()

    payment.allowed = None
    payment.transferred = True
    payment.save()


    record = {"outboundPaymentId":payment.outboundPaymentId,
                "fromAccountNum":payment.fromAccountNum.accountNum,
                "fromPaymentServiceId":payment.fromPaymentServiceId,
                "toAccountNum":payment.toAccountNum,
                "toPaymentServiceId":payment.toPaymentServiceId,
                "amount":payment.amount,
                "transferred":payment.transferred
                }

    return (0, record)

#Create your views here.
class MakeUser(APIView): #DELETE
    def post(self, request):
        body = json.loads(request.body)

        email = body["email"]
        password = body["password"]
        accountNum = body['accountNum']
        paymentServiceId = body['paymentServiceId']
        balance = body['balance']

        if balance <=0:
            return Response({"error": "Balance must be a positive integer"})

        if paymentServiceId != 30:
            return Response({"error": "User not added as the payment service Id wasn't 30"})

        account = Account.objects.filter(Q(accountNum = accountNum)).first()
        if account:
            return Response({"error": "Account number taken. Try again"})

        Account.objects.create_user(email, password, accountNum = accountNum, paymentServiceId=paymentServiceId, balance=balance)
        return Response({"AccountCreated":True})

class Bill(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def post(self, request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["accountNumber", "paymentServiceId", "amount"]
        error = errorChecker(bodyLength=3, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        from_accountNum = body["accountNumber"]
        from_serviceId = body["paymentServiceId"]
        amount = body["amount"]

        if not isinstance(from_accountNum, int) or not isinstance(from_serviceId, int):
            error = "You must provide the account number and payment service ID as integers."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not isinstance(amount, int) and not isinstance(amount, float):
            error = "You must provide the amount as an integer or a float."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if amount <= 0:
            error = "You must provide an amount that is greater than zero."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account = request.user
        to_accountNum = account.accountNum
        to_serviceId = account.paymentServiceId

        if from_serviceId == 30:
            response = createOutboundFunc(from_accountNum, from_serviceId, to_accountNum, to_serviceId, amount)
            if response[0] != 0:
                return Response({"error":response[1]}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            else:
                return Response({"outboundPaymentId":response[1]}, status=status.HTTP_200_OK)

        #Access web directory here to get service given by payment service id
        directoryResponse = requests.get("https://sc19hwam.eu.pythonanywhere.com/directory/payment-services/lookup/?paymentServiceId="+str(from_serviceId))
        if directoryResponse.status_code != 200:
            error = "Error when attempting web directory lookup. The following error was given: "
            error += directoryResponse.json()["error"]
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        hostname = directoryResponse.json()["paymentService"]["hostname"]
        #hostname = "http://127.0.0.1:8000"
        response = requests.post("https://" + hostname + "/payment/outbound/create/", json={"fromAccountNumber":from_accountNum,
                                                                                        "fromPaymentServiceId":from_serviceId,
                                                                                        "toAccountNumber":to_accountNum,
                                                                                        "toPaymentServiceId":to_serviceId,
                                                                                        "amount":amount})

        if response.status_code != 200:
            error = "Error when attempting to create an outbound payment. The following error was given: "
            error += response.json()["error"]
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(response.json(), status=status.HTTP_200_OK)


class Login(APIView):
    def post(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["password", "email"]
        error = errorChecker(bodyLength=2, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        email = body["email"]
        password = body["password"]
        if not isinstance(email, str) or not isinstance(password, str):
            error = "You must pass in the username and password as strings."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        user = authenticate(email=email, password=password)

        if not user:
            error = "Invalid email and password combination."
            return Response({"successful":False, "error":error}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            token = Token.objects.get_or_create(user=user)[0]
            return Response({"successful":True, "accountNumber":user.accountNum, "paymentServiceId":user.paymentServiceId, "token":token.key}, status=status.HTTP_200_OK)


class Logout(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def delete(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        error = errorChecker(bodyLength=0, paramLength=0, body=body, queryParams=request.query_params)
        if error != "":
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        token = Token.objects.get_or_create(user=request.user)[0]
        token.delete()

        return Response({"successful":True}, status=status.HTTP_200_OK)

class Deposit(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def put(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"successful": False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["amount"]
        error = errorChecker(bodyLength=1, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        amount = body["amount"]

        if not isinstance(amount, float) and not isinstance(amount, int):
            error = "You must provide the amount in the form of an integer or a float."
            return Response({"successful": False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if amount <= 0:
            error = "You must provide an amount to deposit that is greater than zero."
            return Response({"successful": False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account = request.user
        account.balance += amount
        account.save()

        return Response({"successful": True}, status=status.HTTP_200_OK)

class GetBalance(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self,request):
        if not request.body:
            body = []
        else:
            body = json.loads(request.body)

        body = json.loads(request.body)

        error = errorChecker(bodyLength=0, paramLength=0, body=body, queryParams=request.query_params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account = request.user

        return Response({"balance":account.balance}, status=status.HTTP_200_OK)


class Exists(APIView):
    def get(self,request):
        if not request.body:
            body = []
        else:
            body = json.loads(request.body)

        params = ["accountNumber"]
        error = errorChecker(bodyLength=0, paramLength=1, body=body, queryParams=request.query_params, requiredQueryParams=params)
        if error != "":
            return Response({"exists":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        accountNum = request.query_params["accountNumber"]

        if not accountNum.isdigit():
            error = "You must provide the account number as an integer."
            return Response({"exists":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        response = existsFunc(accountNum)

        if response[0] != True:
            return Response({"exists":False, "error":response[1]}, status=status.HTTP_200_OK)

        return Response({"exists":True}, status=status.HTTP_200_OK)


class GetDetails(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def get(self,request):
        if not request.body:
            body = []
        else:
            body = json.loads(request.body)

        body = json.loads(request.body)

        error = errorChecker(bodyLength=0, paramLength=0, body=body, queryParams=request.query_params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account = request.user

        return Response({"accountNum":account.accountNum, "paymentServiceId":account.paymentServiceId}, status=status.HTTP_200_OK)

class CreateOutbound(APIView):
    def post(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["fromAccountNumber", "fromPaymentServiceId", "toAccountNumber", "toPaymentServiceId", "amount"]
        error = errorChecker(bodyLength=5, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        from_accountNum = body["fromAccountNumber"]
        from_serviceId = body["fromPaymentServiceId"]
        to_accountNum = body["toAccountNumber"]
        to_serviceId = body["toPaymentServiceId"]
        amount = body["amount"]

        response = createOutboundFunc(from_accountNum, from_serviceId, to_accountNum, to_serviceId, amount)
        if response[0] != 0:
            return Response({"error":response[1]}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            return Response({"outboundPaymentId":response[1]}, status=status.HTTP_200_OK)

class AllowOutbound(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    def put(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["outboundPaymentId"]
        error = errorChecker(bodyLength=1, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        paymentId = body["outboundPaymentId"]
        if not isinstance(paymentId, int):
            error = "You must provide the outbound payment ID as an integer."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        payment = OutboundPayment.objects.filter(Q(outboundPaymentId=paymentId)).first()
        if not payment:
            error = "An outbound payment record with the provided ID could not be found."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account = request.user

        if payment.fromAccountNum.accountNum != account.accountNum or payment.fromPaymentServiceId != account.paymentServiceId:
            error = "This user is not authorised to allow this outbound payment."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if payment.transferred == True:
            error = "This payment transfer could not be allowed as it has already been transferred."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if payment.allowed != None:
            error = "This payment transfer has already been allowed."
            return Response({"approved":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        payment.allowed = timezone.now() + timedelta(minutes=10)
        payment.save()

        return Response({"approved":True}, status=status.HTTP_200_OK)

class TransferOutbound(APIView):
    def put(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["outboundPaymentId", "fromPaymentServiceId"]
        error = errorChecker(bodyLength=2, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        paymentId = body["outboundPaymentId"]
        from_paymentServiceId = body["fromPaymentServiceId"]
        if not isinstance(paymentId, int) or not isinstance(from_paymentServiceId, int):
            error = "You must provide the outbound payment ID and payment service ID as integers."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


        directoryResponse = requests.get("https://sc19hwam.eu.pythonanywhere.com/directory/payment-services/lookup/?paymentServiceId="+str(from_paymentServiceId))
        if directoryResponse.status_code != 200:
            error = "Error when attempting web directory lookup. The following error was given: "
            error += directoryResponse.json()["error"]
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        hostname = directoryResponse.json()["paymentService"]["hostname"]
        #hostname = "http://127.0.0.1:8000"

        private_key = serialization.load_pem_private_key(private_key_pem.encode('utf-8'), password=None)

        signature = private_key.sign(str(paymentId).encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        response = requests.put("https://" + hostname+ "/payment/outbound/redeem/", json={"outboundPaymentId":paymentId,
                                                                        "signature":base64.b64encode(signature).decode('utf-8'),
                                                                        "toPaymentServiceId":30})

        if response.status_code != 200:
            error = "Error when attempting to complete transfer. The following error was given: "
            error += response.json()["error"]
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        amount = response.json()["outboundPaymentRecord"]["amount"]
        accountNum = response.json()["outboundPaymentRecord"]["toAccountNum"]

        account = Account.objects.filter(Q(accountNum = accountNum)).first()
        if not account:
            error = "An account with this account number could not be found."
            return Response({"successful":False, "error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        account.balance += amount
        account.save()

        return Response({"successful":True}, status=status.HTTP_200_OK)

class RedeemOutbound(APIView):
    def put(self,request):
        if not request.body:
            error = "Your request must have a body."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        body = json.loads(request.body)

        params = ["outboundPaymentId", "signature", "toPaymentServiceId"]
        error = errorChecker(bodyLength=3, paramLength=0, body=body, queryParams=request.query_params, requiredBodyParams=params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        paymentServiceId = body["toPaymentServiceId"]
        signature = base64.b64decode(str(body["signature"]).encode('utf-8'))
        outboundId = body["outboundPaymentId"]

        response = redeemFunc(paymentServiceId, signature, outboundId)

        if response[0] != 0:
            return Response({"error":response[1]}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response({"outboundPaymentRecord":response[1]}, status=status.HTTP_200_OK)

class FetchOutbound(APIView):
    def get(self,request):
        if not request.body:
            body = []
        else:
            body = json.loads(request.body)

        params = ["outboundPaymentId"]
        error = errorChecker(bodyLength=0, paramLength=1, body=body, queryParams=request.query_params, requiredQueryParams=params)
        if error != "":
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        paymentId = request.query_params["outboundPaymentId"]

        if not paymentId.isdigit():
            error = "You must provide the outbound payment ID as an integer."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        paymentId = int(paymentId)
        payment = OutboundPayment.objects.filter(Q(outboundPaymentId = paymentId)).first()
        if not payment:
            error = "An outbound payment record with the provided ID could not be found."
            return Response({"error":error}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        record = {"outboundPaymentId":payment.outboundPaymentId,
                 "fromAccountNum":payment.fromAccountNum.accountNum,
                 "fromPaymentServiceId":payment.fromPaymentServiceId,
                 "toAccountNum":payment.toAccountNum,
                 "toPaymentServiceId":payment.toPaymentServiceId,
                 "amount":payment.amount,
                 "transferred":payment.transferred
                 }

        return Response({"outboundPaymentRecord":record}, status=status.HTTP_200_OK)
