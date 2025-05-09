from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/setup/", views.setup, name="setup"),
    path("api/display", views.display, name="display"),
    path("api/log", views.log, name="log"),
    path("api/v1/generate_screen", views.generate_screen, name="generate_screen"),
    path(
        "api/v1/media/<str:filename>", views.device_image_view, name="device_image_view"
    ),
    path("preview", views.preview, name="preview"),
    path("api/v1/battery", views.battery, name="battery"),
]
