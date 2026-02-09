# C:\portale\backend\project_core\urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('modules.auth.urls')),
    path('api/util/', include('modules.util.urls')),
    path('api/', include('modules.plu.urls')),
    path('api/test/', lambda r: HttpResponse("OK")),

    # Tutte le app embed sotto /app/ (una sola regola IIS per sempre)
    path('app/importelab/', include('modules.importelab.urls')),
    path('app/pallet-promoter/', include('modules.pallet_promoter.urls')),
    path('app/alloca-hostess/', include('modules.alloca_hostess.urls')),
    path('app/merchandiser/', include('modules.merchandiser.urls')),
    path('app/welfare/', include('modules.welfare.urls')),
    path('app/asso_articoli/', include('modules.asso_articoli.urls')),
    path('app/scaricopromo/', include('modules.scaricopromo.urls')),
    # Aggiungi qui le nuove app:
    # path('app/magazzino/', include('modules.magazzino.urls')),
    # path('app/ordini/', include('modules.ordini.urls')),
    # ... ecc
]