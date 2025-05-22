from rest_framework import serializers
from .models import Package, Subscription
from django.contrib.auth.models import User

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    package = PackageSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Subscription
        fields = '__all__'
        