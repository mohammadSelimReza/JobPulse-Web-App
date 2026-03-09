from rest_framework import serializers
from .models import (
    User, OTPVerification, JobCategory, Subscription, 
    JobOffer, Blacklist, ContactMessage, SystemSettings
)

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
        fields = ['id', 'phone_number', 'is_admin', 'sms_notification_active']

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
        fields = ['id', 'category', 'category_id', 'subscribed_via', 'is_active', 'subscribed_at', 'last_sms_sent_date']
        read_only_fields = ['subscribed_via', 'is_active', 'subscribed_at', 'last_sms_sent_date']

class JobOfferSerializer(serializers.ModelSerializer):
    category_details = JobCategorySerializer(source='category', read_only=True)
    class Meta:
        model = JobOffer
        fields = '__all__'

class BlacklistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[phone_regex], max_length=17)
    
    class Meta:
        model = Blacklist
        fields = '__all__'

class ContactMessageSerializer(serializers.ModelSerializer):
    number = serializers.CharField(validators=[phone_regex], max_length=17)
    
    class Meta:
        model = ContactMessage
        fields = '__all__'

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ['terms_and_conditions', 'privacy_policy']

class AdminSubscriberSerializer(serializers.ModelSerializer):
    """
    Unified serializer for the Admin CMS to show a user and their active subscriptions
    """
    active_subscriptions = serializers.SerializerMethodField()
    last_sms_sent = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'sms_notification_active', 'active_subscriptions', 'last_sms_sent']

    def get_active_subscriptions(self, obj):
        subs = obj.subscriptions.filter(is_active=True).select_related('category')
        return [sub.category.name for sub in subs]
        
    def get_last_sms_sent(self, obj):
        # Return the most recent sms sent date from any subscription for this user
        subs = obj.subscriptions.filter(is_active=True).order_by('-last_sms_sent_date')
        if subs.exists() and subs.first().last_sms_sent_date:
            return subs.first().last_sms_sent_date
        return None
