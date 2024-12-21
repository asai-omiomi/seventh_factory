from django.shortcuts import redirect
from django.conf import settings

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ログインを要求しないURLを指定
        exempt_urls = ['/', '/login/']
        current_path = request.path

        if not request.user.is_authenticated and current_path not in exempt_urls:
            return redirect(settings.LOGIN_URL)

        response = self.get_response(request)
        return response
