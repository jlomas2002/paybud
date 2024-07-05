# Payment Service REST API

A payment web service written in Python using the Django REST Framework.  
Originally written for a university project and serves as the backend to a larger flight booking and management system.  
Includes proper authentication for certain endpoints, the use of public/private key cryptography to ensure secure transactions,
and robust error checking ensuring only valid transactions can be made.

### Key endpoints:

- payment/account/login/
  - Used to authenticate a user.
- payment/account/logout/
  - Logout of session.
- payment/account/deposit/
  - Deposit money into an account.
- payment/account/balance/
  - Get the balance for an account.
- payment/account/exists/
  - Check if an account exists.
- payment/account/details/
  - Get the details for an account.
- payment/outbound/create/
  - Create an outbound payment transaction.
- payment/outbound/allow/
  - Validate and allow a transaction.
- payment/outbound/transfer/
  - Execute a transaction between two accounts.
- payment/outbound/redeem/
  - Internal endpoint to redeem transfer to recieving account.
