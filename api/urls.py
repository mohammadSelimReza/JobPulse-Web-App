from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RequestOTPView, VerifyOTPView, SubscriptionViewSet, USSDCallbackView,
    JobOfferViewSet, AdminSubscriberViewSet, BlacklistViewSet, DashboardStatsView
)

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'admin/jobs', JobOfferViewSet, basename='admin-jobs')
router.register(r'admin/subscribers', AdminSubscriberViewSet, basename='admin-subscribers')
router.register(r'admin/blacklist', BlacklistViewSet, basename='admin-blacklist')

urlpatterns = [
    path('auth/request-otp/', RequestOTPView.as_view(), name='request_otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/admin-login/', TokenObtainPairView.as_view(), name='admin_login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ussd/callback/', USSDCallbackView.as_view(), name='ussd_callback'),
    path('admin/dashboard-stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('', include(router.urls)),
]
