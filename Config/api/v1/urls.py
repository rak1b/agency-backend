from django.urls import path, include

app_name = 'api-v1'

urlpatterns = [
    path('/auth/web/', include('authentication.api.web.urls')),
    path('/agency-management/web/', include('agency_inventory.api.web.urls')),
    path('/order/web/', include('order.api.web.urls')),
    path('/support/web/', include('support.api.web.urls')),
    # path('/mobile/auth/', include('authentication.api.mobile.urls')),

    # path('account/', include('account.api.urls')),
    # path('product/', include('product.api.urls')),
    # path('support/', include('support.api.urls')),
    # path('auth/', include('coreapp.api.urls')),
    # path('leads/', include('leads.api.urls')),
    # path('quotes/', include('quotes.api.urls')),
    # path('applications/', include('applications.api.urls')),
    # path('products/', include('products.api.urls')),
    # path('invoices/', include('invoices.api.urls')),
    # path('information-hub/', include('informationhub.api.urls')),
]
