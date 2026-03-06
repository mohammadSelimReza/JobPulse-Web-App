import logging
import requests
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from .models import Subscription, JobOffer, Blacklist, SMSDeliveryLog

logger = logging.getLogger(__name__)

# --- Orange SMS API Configuration ---
ORANGE_TOKEN_URL = 'https://api.orange.com/oauth/v3/token'
ORANGE_SMS_URL = 'https://api.orange.com/smsmessaging/v1/outbound/{sender}/requests'
ORANGE_TOKEN_CACHE_KEY = 'orange_sms_access_token'
ORANGE_TOKEN_TTL = 3500  # Slightly less than 3600s to avoid edge-case expiry


def get_orange_access_token():
    """
    Obtain an OAuth2 access token from Orange API.
    Caches the token in Redis/Django cache for reuse across Celery workers.
    """
    # Try cache first
    cached_token = cache.get(ORANGE_TOKEN_CACHE_KEY)
    if cached_token:
        return cached_token

    auth_header = settings.env('ORANGE_AUTH_HEADER', default=None)
    if not auth_header:
        raise ValueError("ORANGE_AUTH_HEADER not configured in .env")

    headers = {
        'Authorization': auth_header,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {'grant_type': 'client_credentials'}

    response = requests.post(ORANGE_TOKEN_URL, headers=headers, data=data, timeout=15)
    response.raise_for_status()

    token_data = response.json()
    access_token = token_data['access_token']

    # Cache the token (expires in ~1 hour, we cache for slightly less)
    cache.set(ORANGE_TOKEN_CACHE_KEY, access_token, ORANGE_TOKEN_TTL)
    logger.info("Orange SMS API access token obtained and cached.")
    return access_token


def send_sms_via_orange(phone_number, message_content, access_token):
    """
    Send a single SMS via the Orange SMS API.
    Phone number should be in international format: +226XXXXXXXX
    """
    sender_address = settings.env('ORANGE_SENDER_ADDRESS', default='tel:+2260000')
    url = ORANGE_SMS_URL.format(sender=requests.utils.quote(sender_address, safe=''))

    # Ensure phone number is in tel: format
    if not phone_number.startswith('tel:'):
        recipient = f'tel:{phone_number}'
    else:
        recipient = phone_number

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'outboundSMSMessageRequest': {
            'address': recipient,
            'senderAddress': sender_address,
            'outboundSMSTextMessage': {
                'message': message_content
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, phone_number, message_content):
    """
    Celery task to send a single SMS via Orange SMS API.
    Used for OTPs, notifications, and daily job broadcasts.
    Retries up to 3 times on transient failures.
    """
    try:
        # Avoid sending to blacklisted numbers
        if Blacklist.objects.filter(phone_number=phone_number).exists():
            logger.info(f"SMS blocked: {phone_number} is blacklisted.")
            return "Blacklisted"

        # Check credentials are configured
        auth_header = settings.env('ORANGE_AUTH_HEADER', default=None)
        if not auth_header or auth_header == 'your_orange_auth_header_here':
            error_msg = "Orange SMS credentials not configured in .env"
            logger.error(error_msg)
            SMSDeliveryLog.objects.create(
                phone_number=phone_number,
                message_content=message_content,
                status='FAILED',
                error_message=error_msg
            )
            return error_msg

        # Get cached or fresh OAuth2 token
        access_token = get_orange_access_token()

        # Send the SMS
        result = send_sms_via_orange(phone_number, message_content, access_token)

        SMSDeliveryLog.objects.create(
            phone_number=phone_number,
            message_content=message_content,
            status='SENT'
        )
        logger.info(f"SMS sent to {phone_number} via Orange API.")
        return str(result)

    except requests.exceptions.HTTPError as e:
        # If token expired (401), invalidate cache and retry
        if e.response is not None and e.response.status_code == 401:
            cache.delete(ORANGE_TOKEN_CACHE_KEY)
            logger.warning(f"Orange token expired, invalidating cache and retrying for {phone_number}.")
            raise self.retry(exc=e)

        logger.error(f"Orange SMS API HTTP error for {phone_number}: {str(e)}")
        SMSDeliveryLog.objects.create(
            phone_number=phone_number,
            message_content=message_content,
            status='FAILED',
            error_message=str(e)
        )
        return str(e)

    except Exception as e:
        logger.error(f"SMS send failed for {phone_number}: {str(e)}")
        SMSDeliveryLog.objects.create(
            phone_number=phone_number,
            message_content=message_content,
            status='FAILED',
            error_message=str(e)
        )
        return str(e)


@shared_task
def send_daily_job_offers():
    """
    Scheduled task to fetch active jobs for the day and send to subscribers via Orange SMS.
    """
    active_jobs = JobOffer.objects.filter(is_active=True, created_at__date=timezone.now().date())

    if not active_jobs.exists():
        logger.info("No active jobs for today.")
        return "No active jobs for today."

    # Group jobs by category
    jobs_by_category = {}
    for job in active_jobs:
        if job.category_id not in jobs_by_category:
            jobs_by_category[job.category_id] = []
        jobs_by_category[job.category_id].append(job)

    # Fetch active subscriptions
    subscriptions = Subscription.objects.filter(is_active=True).select_related('user', 'category')
    queued_count = 0

    for sub in subscriptions:
        category_jobs = jobs_by_category.get(sub.category_id, [])
        if not category_jobs:
            continue

        message_body = f"Sahel Job Offers - {sub.category.name}:\n"
        for job in category_jobs:
            message_body += f"- {job.title}: {job.description[:50]}...\n"

        send_sms_task.delay(sub.user.phone_number, message_body)
        queued_count += 1

    logger.info(f"Daily job offers queued: {queued_count} SMS messages.")
    return f"Daily job offers queued successfully: {queued_count} messages."
