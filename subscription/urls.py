from django.urls import path
from . import views

urlpatterns = [
    path('', views.package_view, name='package'),
    path('subscription/<int:package_id>', views.subscription_create, name='subscription'),
    path('cancel_subscription/<int:subscription_id>', views.cancel_subscription, name='cancel_subscription'),
    path('webhook', views.stripe_webhook_view, name='webhook'),
    path('success', views.success_view, name='success'),
    path('cancel', views.cancel_view, name='cancel'),
    path('my-subscription', views.my_subscription, name='my-subscription')
]