from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.security import django_auth

router = Router(tags=["auth"])


class LoginIn(Schema):
    email: str
    password: str


class Me(Schema):
    email: str


class Detail(Schema):
    detail: str


@router.get("/csrf")
def csrf(request):
    # get_token marks the cookie for the CSRF middleware to set on the response
    return {"csrfToken": get_token(request)}


@router.post("/login", response={200: Me, 401: Detail})
def login_view(request, payload: LoginIn):
    user = authenticate(request, username=payload.email.strip().lower(), password=payload.password)
    if user is None:
        return 401, {"detail": "Nieprawidłowy e-mail lub hasło"}
    login(request, user)
    return 200, {"email": user.email or user.username}


@router.post("/logout", response={204: None}, auth=django_auth)
def logout_view(request):
    logout(request)
    return 204, None


@router.get("/me", response={200: Me}, auth=django_auth)
def me(request):
    return {"email": request.user.email or request.user.username}
