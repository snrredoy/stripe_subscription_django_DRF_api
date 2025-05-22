from django.contrib import admin
from .models import Package, Subscription

# Register your models here.
@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'interval', 'stripe_product_id', 'stripe_price_id', 'discount', 'discount_price', 'is_active')
    list_display_links = ('id', 'name',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'package', 'start_date', 'end_date', 'stripe_subscription_id', 'is_active')
    list_display_links= ('id', 'user', 'package',)