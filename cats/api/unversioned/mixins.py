from django.urls import reverse


class DeprecatedEndpointMixin:
    deprecation_date = "Wed, 01 July 2026 00:00:00 GMT"

    def finalize_response(self, request, response, *args, **kwargs):
        new_url = request.build_absolute_uri(
            reverse(
                f"v1-{request.resolver_match.view_name}",
                kwargs=request.resolver_match.kwargs,
            )
        )
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Deprecation"] = "true"
        response["Sunset"] = self.deprecation_date
        response["Link"] = f"<{new_url}>; rel=\"successor-version\""
        return response