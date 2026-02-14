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

        # Recupero OU e GRUPPI
        conn.search(
            search_base="DC=groscidac,DC=local",
            search_filter=f"(sAMAccountName={username})",
            search_scope=SUBTREE,
            attributes=["distinguishedName", "memberOf"]
        )

        ou_list = []
        group_list = []
        
        if conn.entries:
            entry = conn.entries[0]
            
            # Estrai OU dal DN
            dn = entry.distinguishedName.value
            ou_list = self.extract_all_ous_from_dn(dn)
            
            # Estrai gruppi da memberOf
            if hasattr(entry, 'memberOf') and entry.memberOf:
                group_list = self.extract_groups_from_memberof(entry.memberOf.values)

        conn.unbind()

        # Crea/recupera utente Django
        user_obj, created = User.objects.get_or_create(username=username)
        if created:
            user_obj.set_unusable_password()
            user_obj.save()

        # Combina OU + Gruppi AD
        user_obj.ldap_ous = ou_list
        user_obj.ldap_groups = group_list
        user_obj.all_permissions = ou_list + group_list  # Tutto insieme

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
                if p.upper().startswith("OU="):
                    ou_values.append(p.split("=")[1].lower())
            return ou_values
        except:
            return []

    def extract_groups_from_memberof(self, memberof_list):
        """
        Es: ['CN=Acquisti,OU=Commerciale,...', 'CN=Domain Users,...']
        -> ['acquisti', 'domain users']
        """
        groups = []
        try:
            for member in memberof_list:
                parts = member.split(",")
                for p in parts:
                    if p.upper().startswith("CN="):
                        groups.append(p.split("=")[1].lower())
                        break
        except:
            pass
        return groups