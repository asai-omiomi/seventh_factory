from django.shortcuts import redirect
from django.conf import settings

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ログイン不要なパス（前方一致）
        exempt_prefixes = [
            settings.LOGIN_URL,   # /login/
            '/static/',
        ]

        if not request.user.is_authenticated:
            if not any(request.path.startswith(p) for p in exempt_prefixes):
                return redirect(settings.LOGIN_URL)

        return self.get_response(request)
