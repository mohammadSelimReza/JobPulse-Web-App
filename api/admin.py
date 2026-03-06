from django.contrib import admin
from .models import User, OTPVerification, JobCategory, JobOffer, Subscription, Blacklist, SMSDeliveryLog

admin.site.register(User)
admin.site.register(OTPVerification)
admin.site.register(JobCategory)
admin.site.register(JobOffer)
admin.site.register(Subscription)
admin.site.register(Blacklist)
admin.site.register(SMSDeliveryLog)
