#backends.py
from django.contrib.auth.models import User
from django.conf import settings
from ldap3 import Server, Connection, ALL, SUBTREE


class LDAPBackend:
    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        server = Server(settings.LDAP_SERVER, get_info=ALL)
        full_user = f"{settings.LDAP_DOMAIN}\\{username}"

        try:
            conn = Connection(
                server,
                user=full_user,
                password=password,
                authentication="SIMPLE",
                auto_bind=True
            )
        except Exception:
            return None

        # Recupero OU dal DN
        conn.search(
            search_base="DC=groscidac,DC=local",
            search_filter=f"(sAMAccountName={username})",
            search_scope=SUBTREE,
            attributes=["distinguishedName"]
        )

        ou_list = []
        if conn.entries:
            dn = conn.entries[0].distinguishedName.value
            # Es: CN=Alessandro,OU=ITD,OU=GrosCidac_New,DC=...
            ou_list = self.extract_all_ous_from_dn(dn)

        # Crea/recupera utente Django
        user_obj, created = User.objects.get_or_create(username=username)
        if created:
            user_obj.set_unusable_password()
            user_obj.save()

        # Assegna gruppi OU utilizzabili dal LoginLDAPAPIView
        # (lo leggi come user.ldap_ous)
        user_obj.ldap_ous = ou_list

        return user_obj

    def extract_all_ous_from_dn(self, dn: str):
        """
        Es: 'CN=X,OU=ITD,OU=GrosCidac_New,DC=groscidac,DC=local'
        -> ['itd', 'groscidac_new']
        """
        try:
            parts = dn.split(",")
            ou_values = []
            for p in parts:
                if p.lower().startswith("ou="):
                    ou_values.append(p.split("=")[1].lower())
            return ou_values
        except:
            return []
