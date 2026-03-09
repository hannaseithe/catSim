from drf_spectacular.openapi import AutoSchema
from rest_framework.permissions import IsAuthenticated



class AuthenticatedAutoSchema(AutoSchema):
    def _get_response_bodies(self, direction="response"):
        responses = super()._get_response_bodies(direction)

        # Only modify normal responses
        if direction == "response":
            if getattr(self.view, "permission_classes", None):
                responses.setdefault(
                    "400",
                    {"description": "Invalid Request Data"},
                )
                responses.setdefault(
                    "404",
                    {
                        "description": "Resource not found"
                    }
                )
                if IsAuthenticated in getattr(self.view, "permission_classes", []):
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
    
def filter_v1_endpoints(endpoints, **kwargs):                                                                                                                                               
    return [                                                                                                                                                                                
        (path, path_regex, method, callback)                                                                                                                                                
        for path, path_regex, method, callback in endpoints                                                                                                                                 
        if path.startswith("/api/v1/")                                                                                                                                                      
    ] 
