from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = None
    first_name = None
    last_name = None
    
    phone_number = models.CharField(max_length=20, unique=True)
    is_admin = models.BooleanField(default=False)
    
    sms_notification_active = models.BooleanField(default=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number

class OTPVerification(models.Model):
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.phone_number} - {self.otp_code}"

class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)
    sub_categories = models.JSONField(default=list, blank=True, help_text="List of sub-category names")

    def __str__(self):
        return self.name

class JobOffer(models.Model):
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft')
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name='jobs')
    
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company_website_address = models.URLField(blank=True, null=True)
    company_location = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=50, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Subscription(models.Model):
    SUBSCRIPTION_SOURCES = [
        ('WEB', 'Web Interface'),
        ('USSD', 'USSD'),
        ('ADMIN', 'Admin Upload'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name='subscriptions')
    subscribed_via = models.CharField(max_length=10, choices=SUBSCRIPTION_SOURCES, default='WEB')
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    last_sms_sent_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.user.phone_number} - {self.category.name}"

class Blacklist(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    reason = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone_number

class SMSDeliveryLog(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed')
    ]
    phone_number = models.CharField(max_length=20)
    message_content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phone_number} - {self.status}"

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    number = models.CharField(max_length=20)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.subject}"

class SystemSettings(models.Model):
    terms_and_conditions = models.TextField(blank=True, null=True)
    privacy_policy = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SystemSettings.objects.exists():
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return "System Settings"
