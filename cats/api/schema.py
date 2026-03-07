from drf_spectacular.openapi import AutoSchema


class AuthenticatedAutoSchema(AutoSchema):
    def _get_response_bodies(self, direction="response"):
        responses = super()._get_response_bodies(direction)

        # Only modify normal responses
        if direction == "response":
            if getattr(self.view, "permission_classes", None):
                responses.setdefault(
                    "400",
                    {
                        "description": "Invalid request data"
                    },
                )
                responses.setdefault(
                    "401",
                    {
                        "description": "Authentication credentials were not provided or invalid."
                    },
                )
                responses.setdefault(
                    "403",
                    {"description": "Permission denied."},
                )

        return responses
