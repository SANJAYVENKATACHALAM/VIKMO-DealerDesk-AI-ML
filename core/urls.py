from django.urls import path

from . import views


urlpatterns = [
    # Core
    path(
        "health/",
        views.health,
    ),

    path(
        "products/",
        views.products,
    ),

    path(
        "products/<str:sku>/",
        views.product_detail,
    ),

    path(
        "dealers/",
        views.dealers,
    ),

    path(
        "inventory/<str:sku>/",
        views.inventory_detail,
    ),

    path(
        "orders/",
        views.orders,
    ),

    path(
        "orders/<str:order_number>/",
        views.order_detail,
    ),

    # Dealer Assistant
    path(
        "assistant/chat/",
        views.assistant_chat,
    ),

    # Forecasting
    path(
        "forecast/<str:sku>/",
        views.forecast,
    ),

    path(
        "reorder-suggestions/",
        views.reorder_suggestions,
    ),
]