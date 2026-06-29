# C:\portale\django\project_core\urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.views.generic import RedirectView

urlpatterns = [
    path('favicon.ico', lambda r: HttpResponse(status=204)),
    path('', RedirectView.as_view(url='/portal/'), name='root'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('modules.auth.urls')),
    path('api/util/', include('modules.util.urls')),
    path('api/test/', lambda r: HttpResponse("OK")),

    # Portal Django puro
    path('portal/', include('modules.portal.urls')),
    
    # Tutte le app embed sotto /app/ (una sola regola IIS per sempre)
    path('app/importelab/', include('modules.importelab.urls')),
    path('app/edicola/', include('modules.edicola.urls')),
    path('app/pallet-promoter/', include('modules.pallet_promoter.urls')),
    path('app/alloca-hostess/', include('modules.alloca_hostess.urls')),
    path('app/merchandiser/', include('modules.merchandiser.urls')),
    path('app/welfare/', include('modules.welfare.urls')),
    path('app/asso_articoli/', include('modules.asso_articoli.urls')),
    path('app/scaricopromo/', include('modules.scaricopromo.urls')),
    path('api/active-users/', include('modules.active_users.urls')),
    path('app/stampaoffertefuture/', include('modules.stampaoffertefuture.urls')),
    path('app/plu/', include('modules.plu_web.urls')),
    path('app/caricopromo-reparto/', include('modules.caricopromo_reparto.urls')),
    path('app/masterdata/', include('modules.masterdata.urls')),
    path('app/masterdatacategory/', include('modules.masterdatacategory.urls')),
    path('app/caricopromo-abbig/', include('modules.caricopromo_abbig.urls')),
    path('app/assortimento-abbig/', include('modules.assortimento_abbig.urls')),
    path('app/invenduti/', include('modules.invenduti.urls')),
    path('app/master-ordini/', include('modules.master_ordini.urls')),
    path('app/ordini-bloccati/', include('modules.ordini_bloccati.urls')),
    path('app/art-stato-ord-aperta/', include('modules.art_stato_ord_aperta.urls')),
    path('app/promo-doppie/', include('modules.promo_doppie.urls')),
    path('app/promo-doppie-domani/', include('modules.promo_doppie_domani.urls')),
    path('app/giac-negative/', include('modules.giac_negative.urls')),
    path('app/art-no-ean/', include('modules.art_no_ean.urls')),
    path('app/stesso-prezzo/', include('modules.stesso_prezzo.urls')),
    path('app/prezzo-promo-alto/', include('modules.prezzo_promo_alto.urls')),
    path('app/controllo-legami/', include('modules.controllo_legami.urls')),
    path('app/cursori/', include('modules.cursori.urls', namespace='cursori')),
    path('app/stock-picking/', include('modules.stock_picking.urls')),
    path('app/picking-negativi/', include('modules.picking_negativi.urls')),
    path('app/piano-promo/', include('modules.piano_promo.urls')),
    path('app/rio-fornitori/', include('modules.rio_fornitori.urls', namespace='rio_fornitori')),
    path('app/rio-fornitori-new/', include('modules.rio_fornitori_new.urls', namespace='rio_fornitori_new')),
    path('app/parametri-rio/', include('modules.riordino_pdv.urls', namespace='riordino_pdv')),
    path('app/ricette/',       include('modules.ricette.urls', namespace='ricette')),
    path('app/scarti-gettati/', include('modules.scarti_gettati.urls')),
]