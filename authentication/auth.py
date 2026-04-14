import jwt
from .api.utils.jwt_utils import verify_jwt_token
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class RSAJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None  # No authentication performed
        
        # Expecting Authorization: Token <your-token>
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                raise AuthenticationFailed('Invalid token prefix')
        except ValueError:
            raise AuthenticationFailed('Invalid token format')

        # Verify token with hash signature
        payload = verify_jwt_token(token)

        # Get the user from the payload
        from .models import User
        try:
            user = User.objects.get(id=payload.get('user_id'))
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
        
        return (user, token)