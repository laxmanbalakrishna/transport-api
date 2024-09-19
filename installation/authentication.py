from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import VehicleToken

class VehicleTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Get the authorization header from the request
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            # Split the "Token {token_value}" header
            token_type, token_value = auth_header.split()
        except ValueError:
            raise AuthenticationFailed('Invalid token header format.')

        if token_type != 'Token':
            raise AuthenticationFailed('Invalid token type.')

        # Find the vehicle token in the database
        try:
            vehicle_token = VehicleToken.objects.get(token=token_value)
        except VehicleToken.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        # Return the associated vehicle (user) and token for authentication
        return (vehicle_token.vehicle, vehicle_token)
