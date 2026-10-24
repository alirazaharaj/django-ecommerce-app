from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main_app.dashboard import admin_dashboard, dashboard_ajax_data, remaining_stock_view

urlpatterns = [
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/ajax/', dashboard_ajax_data, name='dashboard_ajax'),
    path('admin/remaining-stock/', remaining_stock_view, name='remaining_stock'),
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)