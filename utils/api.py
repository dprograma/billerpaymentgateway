import hashlib
from django.conf import settings
import requests, json
from datetime import datetime
from requests.auth import HTTPBasicAuth
import os
import time
from django.conf import settings

from utils.helpers import encode_base64, generate_unique_reference, hash_sha512
# from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()


# Get the current datetime
now = datetime.now()
# Get the Unix timestamp in seconds
timestamp = int(now.timestamp())
paystack_key = "sk_test_6a07c528d02891ef390fd6d300eaffbb82dd5e92"
merchant_id = f"4001686OJGUHK01"
terminal_id = f"40016857947"
client_id = f"4001459DHEKNS17"

class Paystack:
	def __init__(self):
		# self.api_key = os.getenv('API_KEY')
		# self.api_secret = os.getenv('API_SECRET')
		self.base_url = "https://api.paystack.co"

	def fetchBanks(self):
		url = f"{self.base_url}/bank"
		headers = {
			"Authorization": f"Bearer {paystack_key}",
			"Content-Type": "application/json"
		}
		params = {
			"country": "nigeria",
			"currency": "NGN",
		}
		x = requests.get(url, headers=headers, params=params)
		return x.json()
	
	def resolveAccount(bank_code, account_number):
		url = f"https://api.paystack.co/bank/resolve"
		headers = {
			"Authorization": f"Bearer {paystack_key}",
			"Content-Type": "application/json"
		}
		params = {
			"bank_code": bank_code,
			"account_number": account_number
		}
		x = requests.get(url, headers=headers, params=params)
		return x.json()
	
	def fetch_customer(email):
		url = f"https://api.paystack.co/customer/{email}"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		x = requests.get(url, headers=headers)
		return x.json()
	
	def update_customer(email, fname, lname, mobile):
		url = f"https://api.paystack.co/customer/{email}"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		data = {
			"first_name": lname,
			"last_name": fname,
			"phone": mobile
		}
		x = requests.put(url, headers=headers, data=json.dumps(data))
		return x.json()

	def create_customer(email,first_name,last_name,phone):
		url = f"https://api.paystack.co/customer"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"email": email,
			"first_name": last_name,
			"last_name": first_name,
			"phone": phone
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def validate_customer(customer,first_name,last_name):
		url = f"https://api.paystack.co/customer/{customer}/identification"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"country": "NG",
			"type": "bank_account",
			"first_name": first_name,
			"last_name": last_name
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def whitelist_customer(customer):
		url = f"https://api.paystack.co/customer/set_risk_action"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		data = {
			"customer": customer,
			"risk_action": "allow"
		}
		x = requests.post(url, headers=headers, data=json.dumps(data))
		return x.json()
	
	def virtual_account(customer, fname, lname, bank):
		url = f"https://api.paystack.co/dedicated_account"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"customer": customer,
			"preferred_bank": bank,
			"first_name": fname,
			"last_name": lname
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def init_payment(email, amount, ref, callback):
		url = f"https://api.paystack.co/transaction/initialize"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"reference": ref,
			"email": email,
			"amount": amount,
			"currency": "NGN",
			"callback_url": callback
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def verify_payment(ref):
		url = f"https://api.paystack.co/transaction/verify/{ref}"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		x = requests.get(url, headers=headers)
		return x.json()
	
	def init_transfer(customer, amount, ref, note):
		url = f"https://api.paystack.co/transfer"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"source": "balance",
			"currency": "NGN",
			"reason": note,
			"amount": amount,
			"recipient": customer,
			"reference": ref
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def finalize_transfer(transfer):
		url = f"https://api.paystack.co/transfer/finalize_transfer"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"transfer_code": transfer
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()
	
	def init_transfer_rec(name, account_nummber, code):
		url = f"https://api.paystack.co/transferrecipient"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {paystack_key}"
		}
		datum = {
			"type": "nuban",
			"name": name,
			"account_number": account_nummber,
			"bank_code": code,
			"currency": "NGN"
		}
		x = requests.post(url, headers=headers, data=json.dumps(datum))
		return x.json()


class CoralPay:
	def __init__(self):
		# self.api_key = os.getenv('API_KEY')
		# self.api_secret = os.getenv('API_SECRET')
		self.base_url = "https://testdev.coralpay.com:5000/GwApi/api/v1"
		self.account_url = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis"
		self.token = self.getToken().get('token')
		self.key = self.getToken().get('key')

	def getToken(self):
		url = f"{self.base_url}/Authentication"
		headers = {
			"Content-Type": "application/json",
		}

		datum = {
			"username": "ojapaXIgaPqMJdRVh%I*NXppJGV)*mo",
			"password": "83Y36$47@P^0TTME@NV?*5MFY8H5I?E8N95#I940",
			"terminalId": terminal_id
		}

		response = requests.post(url=url, headers=headers, data=json.dumps(datum))
		if response.status_code == 200:
			return response.json()
		else:
			raise Exception(f"Failed to get token: {response.status_code}, {response.text}")

	def getBanks(self):
		url = f"{self.account_url}/listOfBanks/"
		reference_no = generate_unique_reference()
		username = settings.CORALPAY_DPWT_USERNAME
		combined_string = f"{reference_no}:{username}"
		hashed_value = hash_sha512(combined_string)
		encoded_value = encode_base64(f"{username}:{hashed_value}")
		# reqUrl = settings.CORALPAY_GET_BANK_LIST_URL
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Basic {encoded_value}",
		}
		response = requests.get(url=url, headers=headers)
		if response.status_code == 200:
			return response.json()
		else:
			raise Exception(f"Failed to get banks: {response.status_code}, {response.text}")
		
	
	def generate_signature(self, merchant_id, trace_id, timestamp):
		signature_string = f"{merchant_id}{trace_id}{timestamp}{self.key}"
		signature = hashlib.sha256(signature_string.encode()).hexdigest()
		return signature


	def invoke_payment(self, customer_email, customer_name, customer_phone, token_user_id, title, description, trace_id, product_id, amount, currency, return_url):
		url = f"{self.base_url}/InvokePayment"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.token}"
		}

		timestamp = int(time.time())
		signature = self.generate_signature(merchant_id, trace_id, timestamp)

		request_payload = {
			"requestHeader": {
				"merchantId": merchant_id,
				"terminalId": terminal_id,
				"timeStamp": timestamp,
				"signature": signature
			},
			"customer": {
				"email": customer_email,
				"name": customer_name,
				"phone": customer_phone,
				"tokenUserId": token_user_id
			},
			"customization": {
				"title": title,
				"description": description
			},
			"traceId": trace_id,
			"productId": product_id,
			"amount": str(amount),
			"currency": currency,
			"returnUrl": return_url
		}

		response = requests.post(url=url, headers=headers, data=json.dumps(request_payload))
		if response.status_code == 200:
			return response.json()
		else:
			raise Exception(f"Failed to invoke payment: {response.status_code}, {response.text}")
	

	def verify_payment(self, trace_id):
		url = f"{self.base_url}/TransactionQuery"
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.token}"
		}

		timestamp = int(time.time())
		signature = self.generate_signature(merchant_id, trace_id, timestamp)

		request_payload = {
			"requestHeader": {
				"merchantId": merchant_id,
				"terminalId": terminal_id,
				"timeStamp": str(timestamp),
				"signature": signature
			},
			"traceId": trace_id
		}

		response = requests.post(url=url, headers=headers, data=json.dumps(request_payload))
		if response.status_code == 200:
			return response.json()
		else:
			raise Exception(f"Failed to invoke payment: {response.status_code}, {response.text}")


	def generate_reserved_account(self, request_type, customer_name, reference_number, customer_id):
		url = f"{self.account_url}/staticAccount"
		reference_no = generate_unique_reference()
		username = settings.CORALPAY_DPWT_USERNAME
		combined_string = f"{reference_no}:{username}"
		hashed_value = hash_sha512(combined_string)
		encoded_value = encode_base64(f"{username}:{hashed_value}")
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Basic {encoded_value}",
		}

		request_payload = {
			"requestHeader": {
				"clientId": client_id,
				"requestType": request_type
			},
			"customerName": customer_name,
			"referenceNumber": reference_number,
			"customerID": customer_id
		}
		print(headers)
		print(username)
		print(hashed_value)

		response = requests.post(url=url, headers=headers, data=json.dumps(request_payload))
		if response.status_code == 200:
			return response.json()
		else:
			raise Exception(f"Failed to generate reserved account: {response.status_code}, {response.text}")


