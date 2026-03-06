from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from .models import OTPVerification, User, Subscription, JobCategory, Blacklist, JobOffer, SMSDeliveryLog
from .serializers import (
    RequestOTPSerializer, VerifyOTPSerializer, UserSerializer,
    SubscriptionSerializer, JobOfferSerializer, BlacklistSerializer
)
from .tasks import send_sms_task
import csv
import io
import random
import logging
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

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
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
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

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, subscribed_via='WEB')

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        # Note: rather than physical deletion, we mark as inactive to keep history

class USSDCallbackView(APIView):
    """
    Webhook for USSD requests.
    Expects typical USSD payload (e.g., phoneNumber, text).
    """
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

        # Simple mock logic for USSD menu:
        # text="" -> Show menu
        # text="1" -> Subscribe to first category
        # text="2" -> Unsubscribe

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

        # USSD providers typically expect plain text responses starting with CON (continue) or END (terminate)
        return Response(response, content_type='text/plain', status=status.HTTP_200_OK)

class JobOfferViewSet(viewsets.ModelViewSet):
    queryset = JobOffer.objects.all()
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
    queryset = User.objects.filter(is_admin=False)
    serializer_class = UserSerializer
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

class BlacklistViewSet(viewsets.ModelViewSet):
    queryset = Blacklist.objects.all()
    serializer_class = BlacklistSerializer
    permission_classes = [permissions.IsAdminUser]

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            "total_subscribers": User.objects.filter(is_admin=False).count(),
            "total_jobs": JobOffer.objects.count(),
            "total_sms_sent": SMSDeliveryLog.objects.filter(status='SENT').count()
        })
