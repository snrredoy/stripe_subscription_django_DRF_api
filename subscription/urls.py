from django.urls import path
from . import views

urlpatterns = [
    path('packages/', views.PackageView.as_view(), name='package'),
    path('packages/<int:pk>', views.PackageView.as_view(), name='package'),
    path('subscription/', views.SubscriptionView.as_view(), name='subscription'),
    path('subscription/<int:package_id>', views.SubscriptionView.as_view(), name='subscription'),

    path('subscription/<int:package_id>/checkout/', views.SubscriptionCreate.as_view(), name='subscription-checkout'),
    path('cancel_subscription/<int:subscription_id>', views.CancelSubscription.as_view(), name='cancel_subscription'),
    path('webhook/', views.stripe_webhook_view, name='webhook'),
]