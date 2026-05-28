from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.views import health

urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.urls")),
]

if settings.FRONTEND_DIST.exists():
    urlpatterns += [
        re_path(
            r"^assets/(?P<path>.*)$",
            serve,
            {"document_root": settings.FRONTEND_DIST / "assets"},
        ),
    ]

urlpatterns += [
    re_path(
        r"^(?!api/|admin/|static/|health/|assets/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
