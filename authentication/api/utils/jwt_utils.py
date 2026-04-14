import os
import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from rest_framework.exceptions import AuthenticationFailed

# Generate an RSA key pair for JWT signing
JWT_ALGORITHM = 'RS256'
PRIVATE_KEY_PATH = os.path.join(settings.BASE_DIR, 'authentication/utils/private.pem')
PUBLIC_KEY_PATH = os.path.join(settings.BASE_DIR, 'authentication/utils/public.pem')
ACCESS_TOKEN_LIFETIME = timedelta(hours=5)
REFRESH_TOKEN_LIFETIME = timedelta(days=1)
def verify_keys_existance():
    if not os.path.exists(PRIVATE_KEY_PATH):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(PRIVATE_KEY_PATH, 'wb') as priv_file:
            priv_file.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )
    
        public_key = private_key.public_key()
        with open(PUBLIC_KEY_PATH, 'wb') as pub_file:
            pub_file.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )

# Load the private and public keys
def load_private_key():
    # Verify Keys Existance
    verify_keys_existance()
    with open(PRIVATE_KEY_PATH, 'rb') as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )

def load_public_key():
    # Verify Keys Existance
    verify_keys_existance()
    with open(PUBLIC_KEY_PATH, 'rb') as key_file:
        return serialization.load_pem_public_key(
            key_file.read()
        )

# Function to generate JWT token
def generate_tokens(payload):
    private_key = load_private_key()
    
    # now datetime
    now = datetime.utcnow()
    
    # Access token expires in 5 hours
    access_exp = now + ACCESS_TOKEN_LIFETIME
    access_payload = {**payload, 'exp': access_exp,'iat': now,'nbf': now, 'type': 'access'}
    access_token = jwt.encode(access_payload, private_key, algorithm=JWT_ALGORITHM)

    # Refresh token expires in 1 day
    refresh_exp = now + REFRESH_TOKEN_LIFETIME
    refresh_payload = {**payload, 'exp': refresh_exp,'iat': now,'nbf': now, 'type': 'refresh'}
    refresh_token = jwt.encode(refresh_payload, private_key, algorithm=JWT_ALGORITHM)

    return access_token, refresh_token

# Function to verify JWT token
def verify_jwt_token(token, token_type='access'):
    public_key = load_public_key()
    try:
        decoded_data = jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])
        if decoded_data.get('type') != token_type:
            raise AuthenticationFailed('Invalid token')  # Invalid token type
        return decoded_data
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token has expired')  # Token expired
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Invalid token') # Invalid token
        