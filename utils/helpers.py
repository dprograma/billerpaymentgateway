import base64
import time
import hashlib
import string
import math
import random
import secrets
import re


def generate_random_string(length=25) -> str:
    chars = string.ascii_letters + string.digits + "-"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_unique_reference(length=13) -> str:
    current_timestamp = str(int(time.time()))

    hex_length = length - len(current_timestamp)

    if hex_length > 0:
        hex_string = "".join(secrets.choice("0123456789") for _ in range(hex_length))
    else:
        hex_string = ""

    return hex_string + current_timestamp


def hash_sha512(text_to_hash) -> str:
    # Create a new sha512 hash object
    hash_object = hashlib.sha512()
    # Update the hash object with the bytes of the string
    hash_object.update(text_to_hash.encode())
    # Get the hexadecimal representation of the digest
    hash_hex = hash_object.hexdigest()
    return hash_hex


def encode_base64(data) -> str:
    # Encode the data using Base64 encoding
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def generate_current_timestamp() -> str:
    return str(int(time.time()))


def hash_sha256(text_to_hash) -> str:
    # Create a new sha512 hash object
    hash_object = hashlib.sha256()
    # Update the hash object with the bytes of the string
    hash_object.update(text_to_hash.encode())
    # Get the hexadecimal representation of the digest
    hash_hex = hash_object.hexdigest()
    return hash_hex


def generate_ussd_signature(data):
    return hash_sha256(data)


def is_nigerian_phone_number(phone_number):
    # Define the regular expression pattern for a Nigerian phone number
    # The pattern matches a phone number that starts with +234 or 0, followed by 10 digits
    pattern = r"^(?:\+234|234|0)[789]\d{9}$"
    
    # Use re.match to check if the phone number matches the pattern
    if re.match(pattern, phone_number):
        return True
    else:
        return False


def is_valid_email(email):
    # define a regular expression pattern to match email addresses
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # use the re.match function to match the pattern against the email address
    match = re.match(pattern, email)

    # if the match object is not None, the email address is valid
    return match is not None

def validate_amount(amount):
    pattern = r'^\d+(\.\d{1,2})?$'
    if not re.match(pattern, amount):
        return False
    elif float(amount) < 0:
        return False
    else:
        return True


def validate_password_strength(value):
    l, u, p, d = 0, 0, 0, 0
    """Validates that a password is as least 7 characters long and has at least
    1 digit and 1 letter.
    """
    min_length = 7
    if (len(value) >= 7):
        for i in value:

            # counting lowercase alphabets
            if (i.islower()):
                l+=1

            # counting uppercase alphabets
            if (i.isupper()):
                u+=1

            # counting digits
            if (i.isdigit()):
                d+=1

            # counting the mentioned special characters
            if(i=='@'or i=='$' or i=='_' or i == '%'):
                p+=1
    else:
        return f"Password must be at least {min_length} characters long"
    if l < 1:
        return "Password must contain a lowercase."
    elif u < 1:
        return "Password must contain an uppercase."
    elif d < 1:
        return "Password must contain a digit."
    elif p < 1:
        return "Password must contain any of these @, %, $, _"
    else:
        return None


def GenerateOTP(length):
    digits = "0123456789"
    OTP = ""
    for i in range(length):
        OTP += digits[math.floor(random.random() * 10)]
    return OTP


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    characters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(characters) for i in range(length))
    return f"OjaPAY_{result_str}"