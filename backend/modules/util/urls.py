from django.urls import include, path
from modules.util.views import db_test, ldap_login_test

urlpatterns = [
    path("api/auth/", include("modules.auth.urls")),
    path("test-db/", db_test),
    path("login-ldap-test/", ldap_login_test),
]
