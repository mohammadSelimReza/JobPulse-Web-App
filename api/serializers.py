from rest_framework import serializers
from .models import User, OTPVerification, JobCategory, Subscription, JobOffer, Blacklist

from django.core.validators import RegexValidator

# E.164 format validator: e.g. +1234567890
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=17)

class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=17)
    otp_code = serializers.CharField(max_length=6)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'is_admin']

class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = '__all__'

class SubscriptionSerializer(serializers.ModelSerializer):
    category = JobCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=JobCategory.objects.all(), source='category', write_only=True
    )

    class Meta:
        model = Subscription
        fields = ['id', 'category', 'category_id', 'subscribed_via', 'is_active', 'subscribed_at']
        read_only_fields = ['subscribed_via', 'is_active', 'subscribed_at']

class JobOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOffer
        fields = '__all__'

class BlacklistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=17)
    
    class Meta:
        model = Blacklist
        fields = '__all__'

