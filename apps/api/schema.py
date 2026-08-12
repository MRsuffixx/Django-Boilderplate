from drf_spectacular.extensions import OpenApiAuthenticationExtension


class StatusAwareJWTScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authentication.jwt.StatusAwareJWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}


class APIKeyScheme(OpenApiAuthenticationExtension):
    target_class = "apps.api_keys.authentication.APIKeyAuthentication"
    name = "apiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "X-API-Key"}
