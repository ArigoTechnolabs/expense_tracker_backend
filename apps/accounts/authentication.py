import uuid
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that checks if the jwt_key in the token
    matches the jwt_key in the user model.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        # Get jwt_key from token payload
        token_jwt_key = validated_token.get("jwt_key")

        # Check if the key matches the one in database
        if user.jwt_key and token_jwt_key != user.jwt_key:
            raise AuthenticationFailed(
                "Token is invalid (logged in on another device)", code="user_logged_out"
            )

        return user


def rotate_jwt_key(user):
    """
    Generates a new jwt_key for the user, effectively logging them out
    from all other devices.
    """
    user.jwt_key = str(uuid.uuid4())
    user.save()
    return user.jwt_key


try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
        target_class = "apps.accounts.authentication.CustomJWTAuthentication"
        name = "bearerAuth"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }

except ImportError:
    pass
