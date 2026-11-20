from django.urls import path

from . import views

app_name = "bookkeeping"

urlpatterns = [
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/add/", views.transaction_create, name="transaction_create"),
    path("transactions/<int:pk>/edit/", views.transaction_update, name="transaction_update"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("contacts/<slug:kind>/", views.contact_list, name="contact_list"),
    path("contacts/<slug:kind>/add/", views.contact_create, name="contact_create"),
    path("contacts/<slug:kind>/<int:pk>/edit/", views.contact_update, name="contact_update"),
    path("contacts/<slug:kind>/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
]
