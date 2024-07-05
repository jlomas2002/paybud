import requests, json

# #delete all users
# # response = requests.get("http://127.0.0.1:8000/deleteAllUsers")
# # print(response.json())

# response = requests.post("https://ed19j5l.pythonanywhere.com/makeUser/", json={"email":"danburn@gmail.com", "password":"password", 
#                                                                "accountNum":105, "paymentServiceId":30, "balance":1000})
# print(response.json())

# response = requests.post("https://sc20th.pythonanywhere.com/payment/account/login/", json={"email":"tom@email.com", "password":"web12345"})
# print(response.json())
# tomtoken = response.json()["token"]

# response = requests.put("https://sc20th.pythonanywhere.com/payment/account/deposit/", json={"amount": -5}, headers={"Authorization": "Token " + tomtoken})
# print(response.json())

response = requests.post("https://ed19j5l.pythonanywhere.com/payment/account/login/", json={"email":"joe@gmail.com", "password":"password"})
print(response.json())
joetoken = response.json()["token"]

response = requests.get("https://ed19j5l.pythonanywhere.com/payment/account/balance/", json={}, headers={"Authorization": "Token " + joetoken})
print("\n\njoes balance before deposit: " + str(response.json()["balance"]))

response = requests.put("https://ed19j5l.pythonanywhere.com/payment/account/deposit/", json={"amount":100},
                                                                            headers={"Authorization": "Token " + joetoken})
print(response.json())

response = requests.get("https://ed19j5l.pythonanywhere.com/payment/account/balance/", json={}, headers={"Authorization": "Token " + joetoken})
print("\n\njoes balance before deposit: " + str(response.json()["balance"]))

# response = requests.post("https://sc20th.pythonanywhere.com/payment/bill/", json={"accountNumber":100, "paymentServiceId":30, 
#                                                                                 "amount":30},
#                                                                  headers={"Authorization": "Token " + tomtoken})
# print(response.json())
# paymentid = response.json()["outboundPaymentId"]

# # response = requests.post("http://127.0.0.1:8000/payment/account/login/", json={"email":"allan@gmail.com", "password":"password"})
# # print(response.json())
# # allantoken = response.json()["token"]

# response = requests.put("https://ed19j5l.pythonanywhere.com/payment/outbound/allow/", json={"outboundPaymentId":paymentid},
#                                                                             headers={"Authorization": "Token " + joetoken})
# print(response.json())


# response = requests.get("https://ed19j5l.pythonanywhere.com/payment/account/balance/", json={}, headers={"Authorization": "Token " + joetoken})
# print("\n\njoes balance before transfer: " + str(response.json()["balance"]))
# print("Beginning Transfer...")


# response = requests.get("https://sc20th.pythonanywhere.com/payment/account/balance/", json={}, headers={"Authorization": "Token " + tomtoken})
# print("\n\ntoms balance after transfer: " + str(response.json()["balance"]))
# response = requests.get("https://ed19j5l.pythonanywhere.com/payment/account/balance/", json={}, headers={"Authorization": "Token " + joetoken})
# print("\n\njoes balance after transfer: " + str(response.json()["balance"]))
