from django.contrib.sessions.models import Session
from django.utils import timezone

username_target = 'alessandro.novaria'
eliminati = 0
for s in Session.objects.filter(expire_date__gte=timezone.now()):
    data = s.get_decoded()
    if data.get('user', {}).get('username', '').lower() == username_target.lower():
        s.delete()
        eliminati += 1

print(f"Sessioni eliminate per '{username_target}': {eliminati}")
