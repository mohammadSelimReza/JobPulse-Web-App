from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

from .models import (
    OTPVerification, User, Subscription, JobCategory, 
    Blacklist, JobOffer, SMSDeliveryLog, ContactMessage, SystemSettings
)
from .serializers import (
    RequestOTPSerializer, VerifyOTPSerializer, UserSerializer,
    SubscriptionSerializer, JobOfferSerializer, BlacklistSerializer,
    ContactMessageSerializer, SystemSettingsSerializer, AdminSubscriberSerializer,
    JobCategorySerializer
)
from .tasks import send_sms_task
import csv
import io
import random
import logging
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

# --- Auth APIs ---
class RequestOTPView(APIView):
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = str(random.randint(100000, 999999))
            expires_at = timezone.now() + timedelta(minutes=10)
            
            OTPVerification.objects.create(
                phone_number=phone_number,
                otp_code=otp_code,
                expires_at=expires_at
            )
            
            send_sms_task.delay(phone_number, f"Your Sahel Job Offers OTP is: {otp_code}")
            print(otp_code)
            return Response({"message": f"OTP sent successfully {otp_code}"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = serializer.validated_data['otp_code']
            
            try:
                verification = OTPVerification.objects.filter(
                    phone_number=phone_number,
                    otp_code=otp_code,
                    is_verified=False,
                    expires_at__gt=timezone.now()
                ).latest('created_at')
                
                verification.is_verified = True
                verification.save()
                
                user, created = User.objects.get_or_create(phone_number=phone_number)
                
                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "OTP verified successfully",
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)

            except OTPVerification.DoesNotExist:
                return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Webhook ---
class USSDCallbackView(APIView):
    def post(self, request):
        logger.info(f"Received USSD Webhook payload: {request.data}")
        phone_number = request.data.get('phoneNumber')
        if isinstance(phone_number, list):
            phone_number = phone_number[0]
            
        text = request.data.get('text', '')
        if isinstance(text, list):
            text = text[0]

        if not phone_number:
            return Response("END Phone number is required", content_type='text/plain')

        user, _ = User.objects.get_or_create(phone_number=phone_number)
        
        if Blacklist.objects.filter(phone_number=phone_number).exists():
            return Response("END Your number is blacklisted and cannot subscribe.", content_type='text/plain')

        if text == '':
            response = "CON Welcome to Sahel Job Offers\n1. Subscribe to General Jobs\n2. Unsubscribe"
        elif text == '1':
            category, _ = JobCategory.objects.get_or_create(name="General Jobs")
            Subscription.objects.get_or_create(user=user, category=category, defaults={'subscribed_via': 'USSD', 'is_active': True})
            response = "END You have successfully subscribed to General Jobs."
        elif text == '2':
            Subscription.objects.filter(user=user).update(is_active=False)
            response = "END You have successfully unsubscribed from all job alerts."
        else:
            response = "END Invalid input. Please try again."

        return Response(response, content_type='text/plain', status=status.HTTP_200_OK)


# --- ADMIN CMS ENDPOINTS ---

class AdminDashboardStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=6)

        # Overview Stats
        total_job_offers = JobOffer.objects.count()
        total_active_subscribers = User.objects.filter(
            is_admin=False, 
            subscriptions__is_active=True
        ).distinct().count()
        sms_sent_today = SMSDeliveryLog.objects.filter(
            status='SENT', 
            sent_at__date=today
        ).count()
        total_sms_sent = SMSDeliveryLog.objects.filter(status='SENT').count()

        # Dummy Cost Estimator (assuming 1 SMS = 0.05 currency units)
        total_orange_api_cost_on_sms = total_sms_sent * 0.05

        # SMS Performance past 7 days
        sms_logs = SMSDeliveryLog.objects.filter(
            sent_at__date__gte=seven_days_ago, 
            sent_at__date__lte=today
        ).annotate(date=TruncDate('sent_at')).values('date', 'status').annotate(count=Count('id'))
        
        sms_performance = {}
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            day_name = day.strftime('%A').lower()
            sms_performance[day_name] = {"sms_sent_tried": 0, "sms_succesfully_sent": 0}

        for log in sms_logs:
            day_name = log['date'].strftime('%A').lower()
            sms_performance[day_name]["sms_sent_tried"] += log['count']
            if log['status'] == 'SENT':
                sms_performance[day_name]["sms_succesfully_sent"] += log['count']

        # User Growth past 7 days
        users = User.objects.filter(
            is_admin=False, 
            date_joined__date__gte=seven_days_ago,
            date_joined__date__lte=today
        ).annotate(date=TruncDate('date_joined')).values('date').annotate(count=Count('id'))

        user_subscribers_growth = {}
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            day_name = day.strftime('%A').lower()
            user_subscribers_growth[day_name] = 0

        for user in users:
            day_name = user['date'].strftime('%A').lower()
            user_subscribers_growth[day_name] += user['count']

        return Response({
            "overview": {
                "total_job_offers": total_job_offers,
                "total_active_subscribers": total_active_subscribers,
                "sms_sent_today": sms_sent_today,
                "total_sms_sent": total_sms_sent,
                "total_orange_api_cost_on_sms": round(total_orange_api_cost_on_sms, 2)
            },
            "sms_performance": sms_performance,
            "user_subscribers_growth": user_subscribers_growth
        })

class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.IsAdminUser]

class AdminJobOfferViewSet(viewsets.ModelViewSet):
    queryset = JobOffer.objects.all().order_by('-created_at')
    serializer_class = JobOfferSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            jobs_created = 0
            for row in reader:
                title = row.get('title')
                if not title:
                    continue # Skip empty titles
                    
                category_name = row.get('category', 'General Jobs')
                category, _ = JobCategory.objects.get_or_create(name=category_name)
                JobOffer.objects.create(
                    title=title,
                    description=row.get('description', ''),
                    category=category
                )
                jobs_created += 1
                
            logger.info(f"Bulk uploaded {jobs_created} jobs via Admin API.")
            return Response({"message": f"{jobs_created} jobs uploaded successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error processing Job Bulk Upload CSV: {str(e)}")
            return Response({"error": "Invalid CSV format"}, status=status.HTTP_400_BAD_REQUEST)

class AdminSubscriberViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_admin=False).prefetch_related('subscriptions__category').distinct()
    serializer_class = AdminSubscriberSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            subs_created = 0
            
            for row in reader:
                phone_number = row.get('phone_number')
                category_name = row.get('category', 'General Jobs')
                
                if not phone_number or Blacklist.objects.filter(phone_number=phone_number).exists():
                    continue
                    
                user, _ = User.objects.get_or_create(phone_number=phone_number)
                category, _ = JobCategory.objects.get_or_create(name=category_name)
                
                Subscription.objects.get_or_create(
                    user=user, category=category, defaults={'subscribed_via': 'ADMIN'}
                )
                subs_created += 1
                
            logger.info(f"Admin bulk uploaded {subs_created} new subscribers.")
            return Response({"message": f"{subs_created} subscribers added successfully"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error processing Subscriber Bulk Upload CSV: {str(e)}")
            return Response({"error": "Invalid CSV format"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action_type = request.data.get('action') # "unsubscribe" or "blacklist"
        phone_numbers = request.data.get('phone_numbers', [])
        
        if not action_type or not phone_numbers:
            return Response({"error": "action and phone_numbers are required"}, status=400)
            
        users = User.objects.filter(phone_number__in=phone_numbers)
        
        if action_type == 'unsubscribe':
            Subscription.objects.filter(user__in=users).update(is_active=False)
            return Response({"message": f"Successfully unsubscribed {users.count()} users."})
            
        elif action_type == 'blacklist':
            Subscription.objects.filter(user__in=users).update(is_active=False)
            Blacklist.objects.bulk_create([
                Blacklist(phone_number=u.phone_number, reason="Admin Bulk Blacklist") 
                for u in users if not Blacklist.objects.filter(phone_number=u.phone_number).exists()
            ])
            return Response({"message": f"Successfully blacklisted requested users."})
            
        return Response({"error": "Invalid action"}, status=400)

class AdminSystemSettingsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, type):
        settings, _ = SystemSettings.objects.get_or_create(id=1)
        if type == 'terms':
            return Response({"terms": settings.terms_and_conditions})
        elif type == 'privacy':
            return Response({"policy": settings.privacy_policy})
        return Response({"error": "Invalid type"}, status=400)

    def post(self, request, type):
        settings, _ = SystemSettings.objects.get_or_create(id=1)
        if type == 'terms':
            settings.terms_and_conditions = request.data.get('terms', '')
            settings.save()
            return Response({"message": "Terms updated", "terms": settings.terms_and_conditions})
        elif type == 'privacy':
            settings.privacy_policy = request.data.get('policy', '')
            settings.save()
            return Response({"message": "Privacy policy updated", "policy": settings.privacy_policy})
        return Response({"error": "Invalid type"}, status=400)


# --- USER JOURNEY / WEBSITE ENDPOINTS ---

class ContactUsView(APIView):
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Message sent successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PublicPagesView(APIView):
    def get(self, request, type):
        settings, _ = SystemSettings.objects.get_or_create(id=1)
        if type == 'terms':
            return Response({"terms": settings.terms_and_conditions})
        elif type == 'privacy':
            return Response({"policy": settings.privacy_policy})
        return Response({"error": "Invalid type"}, status=400)

class UserCategoryListView(APIView):
    """List all categories with ID so the user can pick which to subscribe to."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        categories = JobCategory.objects.all().order_by('name')
        return Response(JobCategorySerializer(categories, many=True).data)

class UserCategorySubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        category_ids = request.data.get('categories', [])
        if not isinstance(category_ids, list):
            return Response({"error": "Categories must be a list of IDs"}, status=400)
            
        user = request.user
        
        if Blacklist.objects.filter(phone_number=user.phone_number).exists():
            return Response({"error": "Your number is blacklisted and cannot subscribe."}, status=403)
            
        # Deactivate all current subscriptions not in the selected list
        Subscription.objects.filter(user=user).exclude(category_id__in=category_ids).update(is_active=False)
        
        # Activate/Create new ones
        for cat_id in category_ids:
            try:
                category = JobCategory.objects.get(id=cat_id)
                Subscription.objects.update_or_create(
                    user=user, category=category,
                    defaults={'is_active': True, 'subscribed_via': 'WEB'}
                )
            except JobCategory.DoesNotExist:
                continue
                
        active_subs = Subscription.objects.filter(user=user, is_active=True)
        return Response({
            "message": "Subscriptions updated",
            "active_categories": [sub.category.name for sub in active_subs]
        })

class UserSMSPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        preview_text = "Sahel IntelligenceIT\n\nJob Category: IT Developer - XYZ Corp - Ouagadougou - call: +22612345678"
        return Response({"preview": preview_text})

class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        categories = JobCategory.objects.all()
        active_subscriptions = Subscription.objects.filter(user=user, is_active=True).values_list('category_id', flat=True)
        
        if active_subscriptions:
            jobs = JobOffer.objects.filter(category_id__in=active_subscriptions, status='published').order_by('-created_at')
        else:
            jobs = JobOffer.objects.filter(status='published').order_by('-created_at')
            
        return Response({
            "categories": JobCategorySerializer(categories, many=True).data,
            "jobs": JobOfferSerializer(jobs, many=True).data
        })

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = AdminSubscriberSerializer(user)
        total_sms_received = SMSDeliveryLog.objects.filter(phone_number=user.phone_number, status='DELIVERED').count()
        
        data = serializer.data
        data['total_sms_received'] = total_sms_received
        return Response(data)

    def patch(self, request):
        user = request.user
        phone_number = request.data.get('phone_number')
        sms_notification_active = request.data.get('sms_notification_active')
        
        if phone_number and phone_number != user.phone_number:
            if User.objects.filter(phone_number=phone_number).exists():
                return Response({"error": "Phone number already exists"}, status=400)
            user.phone_number = phone_number
            
        if sms_notification_active is not None:
            user.sms_notification_active = sms_notification_active
            
        user.save()
        return Response(UserSerializer(user).data)

class UserUnsubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        Subscription.objects.filter(user=user).update(is_active=False)
        user.sms_notification_active = False
        user.save()
        
        last_sms = SMSDeliveryLog.objects.filter(phone_number=user.phone_number).order_by('-sent_at').first()
        last_sms_date = last_sms.sent_at if last_sms else None
        
        return Response({
            "phone_number": user.phone_number,
            "status": "unsubscribed",
            "last_sms_sent": last_sms_date
        })

# --- For legacy backwards compatibility with previous endpoints ---
class BlacklistViewSet(viewsets.ModelViewSet):
    queryset = Blacklist.objects.all()
    serializer_class = BlacklistSerializer
    permission_classes = [permissions.IsAdminUser]

