from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import User, OTPVerification, JobCategory, JobOffer, Subscription, Blacklist
from django.utils import timezone
from datetime import timedelta

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_request_otp(self):
        url = reverse('request_otp')
        data = {'phone_number': '+123456789'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTPVerification.objects.filter(phone_number='+123456789').exists())

    def test_verify_otp(self):
        phone_number = '+987654321'
        otp_code = '123456'
        OTPVerification.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        url = reverse('verify_otp')
        data = {'phone_number': phone_number, 'otp_code': otp_code}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertTrue(User.objects.filter(phone_number=phone_number).exists())

class SubscriptionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(phone_number='+111222333')
        self.category = JobCategory.objects.create(name='IT Jobs')
        self.client.force_authenticate(user=self.user)

    def test_create_subscription(self):
        url = reverse('user_category_subscribe')
        data = {'categories': [self.category.id]}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Subscription.objects.filter(user=self.user, category=self.category, is_active=True).exists())

class USSDWebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('ussd_callback')
        
    def test_ussd_menu(self):
        data = {'phoneNumber': '+777888999', 'text': ''}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.decode().strip('"').startswith('CON'))

    def test_ussd_subscribe(self):
        data = {'phoneNumber': '+777888999', 'text': '1'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.decode().strip('"').startswith('END'))
        self.assertTrue(Subscription.objects.filter(user__phone_number='+777888999').exists())

    def test_blacklisted_ussd(self):
        phone_number = '+999000111'
        Blacklist.objects.create(phone_number=phone_number)
        
        data = {'phoneNumber': phone_number, 'text': '1'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('blacklisted' in response.content.decode())
        self.assertFalse(Subscription.objects.filter(user__phone_number=phone_number).exists())

class AdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create(phone_number='+0000000', is_admin=True, is_staff=True)
        self.client.force_authenticate(user=self.admin_user)
        
    def test_dashboard_stats(self):
        # Create user
        u = User.objects.create(phone_number='+111')
        c = JobCategory.objects.create(name='Test Category')
        Subscription.objects.create(user=u, category=c, is_active=True)
        
        url = reverse('dashboard_stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['overview']['total_active_subscribers'], 1)

    def test_bulk_upload_jobs(self):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        csv_content = b"title,category,description\nSoftware Engineer,IT Jobs,Great job\nNurse,Health,Hospital job"
        csv_file = SimpleUploadedFile("jobs.csv", csv_content, content_type="text/csv")
        
        url = reverse('admin-jobs-bulk-upload')
        response = self.client.post(url, {'file': csv_file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JobOffer.objects.count(), 2)
        self.assertTrue(JobCategory.objects.filter(name='IT Jobs').exists())
