from django.urls import path
from .views import LoginLDAPAPIView
from modules.util.views import db_test, ldap_login_test

urlpatterns = [
    path("login-ldap/", LoginLDAPAPIView.as_view(), name="login-ldap"),
    path("test-db/", db_test, name="test-db"),
    path("login-ldap-test/", ldap_login_test, name="login-ldap-test"),
]
