from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from accounts.api import router as auth_router
from devices.api import admin as devices_admin
from devices.api import public as devices_public
from devices.api_v1 import urlpatterns as api_v1_urls
from devices.reports import router as reports_router
from integrations.api import router as integrations_router

api = NinjaAPI(
    title="Misja AED API",
    version="0.1.0",
    description="AED data from many sources, synced, merged and exported for dane.gov.pl. See docs/api.md.",
)
api.add_router("/auth", auth_router)
api.add_router("", devices_public)
api.add_router("", devices_admin)
api.add_router("", integrations_router)
api.add_router("", reports_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    *api_v1_urls,  # /api/v1: the versioned Standard API, before the unversioned /api/
    path("api/", api.urls),
]
