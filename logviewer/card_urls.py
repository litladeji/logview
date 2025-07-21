from django.urls import path, re_path
from django.views.static import serve
from django.views.generic import RedirectView
from django.conf.urls.static import static
from . import card_views as views
from card_db.settings import MEDIA_ROOT, MEDIA_URL, DEBUG

app_name = 'cards'

urlpatterns = [
    #url(r'^catalog$', views.CatalogView.as_view(), name='catalog'),
    path('', RedirectView.as_view(url='catalog')),
    path('catalog', views.catalog, name='catalog'),
    path('summary', views.summary, name='summary'),
    path('testers', views.TestersView.as_view(), name='testers'),
    path('stats', views.stats, name='stats'),
    path('test-details', views.TestDetailsView.as_view(), name='test-details'),
    #path('<str:filepath_url>' ,views.detail, name='detail-uid'),
    #path('NO_ID/', views.detail, {"card":'NO_ID'}),
    #path(r'^NO_ID/(?P<test>.*)$', views.testDetail, name='testDetail-uid'),
    #re_path(r'^(?P<card>[0-9]{14})', views.detail, name='detail-uid',{"card":"NO_ID"}),
    re_path(r'^uid/(?P<card>[a-fA-F0-9]{8,16})/calibration$', views.calibration, name='calibration-uid'),
    re_path(r'^uid/(?P<card>[a-fA-F0-9]{8,16})/calibration/(?P<group>[0-9]{1,2})/plots$', views.calPlots, name='plotview-uid'),
    re_path(r'^uid/(?P<card>[a-fA-F0-9]{8,16})/calibration/(?P<group>[0-9]{1,2})/results$', views.calResults, name='results-uid'),
    re_path(r'^uid/(?P<card>[a-fA-F0-9]{8,16})/(?P<test>.*)$', views.testDetail, name='testDetail-uid'),
    re_path(r'^media/(?P<path>.*)$', serve, kwargs={'document_root': MEDIA_ROOT}),
    path("MissingID", views.detail, name='detail'),
    path("<card>/<test>",views.testDetail, name='testDetail-uid'),
    path("<card>/", views.detail, name='detail'),
    re_path(r'^(?P<card>[a-sA-M0-9]{3,10})/$', views.detail, name='detail'),
    re_path(r'^(?P<card>[0-9]{3,7})/calibration$', views.calibration, name='calibration'),
    re_path(r'^(?P<card>[0-9]{3,7})/calibration/(?P<group>[0-9]{1,2})/plots$', views.calPlots, name='plotview'),
    re_path(r'^(?P<card>[0-9]{3,7})/calibration/(?P<group>[0-9]{1,2})/results$', views.calResults, name='results'),
    re_path(r'^(?P<card>[0-9]{3,7})/(?P<test>.*)$', views.testDetail, name='testDetail'),
    path('error', views.error, name='error'),
    re_path(r'^media/(?P<path>.*)$',serve, {'document_root':MEDIA_ROOT,'show_indexes':True}),
    path('plots', views.PlotView.as_view(), name='plots'),
    path('field', views.fieldView, name='fieldView'),
]

if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)