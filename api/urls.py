from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RequestOTPView, VerifyOTPView, USSDCallbackView,
    AdminDashboardStatsView, AdminCategoryViewSet, AdminJobOfferViewSet, 
    AdminSubscriberViewSet, AdminSystemSettingsView, BlacklistViewSet,
    ContactUsView, PublicPagesView, UserCategoryListView, UserCategorySubscribeView, 
    UserSMSPreviewView, UserDashboardView, UserProfileView, UserUnsubscribeView
)

router = DefaultRouter()
# Legacy & Webhook
router.register(r'admin/blacklist', BlacklistViewSet, basename='admin-blacklist')

# Admin API
router.register(r'admin/categories', AdminCategoryViewSet, basename='admin-category')
router.register(r'admin/jobs', AdminJobOfferViewSet, basename='admin-jobs')
router.register(r'admin/subscribers', AdminSubscriberViewSet, basename='admin-subscribers')

urlpatterns = [
    # Auth
    path('auth/request-otp/', RequestOTPView.as_view(), name='request_otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('auth/admin-login/', TokenObtainPairView.as_view(), name='admin_login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Webhook
    path('ussd/callback/', USSDCallbackView.as_view(), name='ussd_callback'),
    
    # Admin CMS
    path('admin/dashboard-stats/', AdminDashboardStatsView.as_view(), name='dashboard_stats'),
    path('admin/settings/<str:type>/', AdminSystemSettingsView.as_view(), name='admin_settings'),
    
    # Website (User Journey)
    path('contact/', ContactUsView.as_view(), name='contact_us'),
    path('pages/<str:type>/', PublicPagesView.as_view(), name='public_pages'),
    path('user/categories/', UserCategoryListView.as_view(), name='user_category_list'),
    path('user/categories/subscribe/', UserCategorySubscribeView.as_view(), name='user_category_subscribe'),
    path('user/sms-preview/', UserSMSPreviewView.as_view(), name='user_sms_preview'),
    path('user/dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('user/profile/', UserProfileView.as_view(), name='user_profile'),
    path('user/unsubscribe/', UserUnsubscribeView.as_view(), name='user_unsubscribe'),

    path('', include(router.urls)),
]
