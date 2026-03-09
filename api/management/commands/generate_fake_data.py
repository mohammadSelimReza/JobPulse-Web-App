import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from api.models import (
    JobCategory, JobOffer, User, Subscription, 
    SMSDeliveryLog, ContactMessage, Blacklist
)

class Command(BaseCommand):
    help = 'Generates 200-300 rows of fake data using Faker for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing Faker...")
        fake = Faker('fr_FR')  # Using French locale as the project is based in Burkina Faso
        
        # 1. Create Categories
        categories_data = ['IT & Technologie', 'Santé & Médical', 'BTP & Construction', 'Éducation', 'Finance & Banque', 'Agriculture']
        categories = []
        for name in categories_data:
            cat, created = JobCategory.objects.get_or_create(
                name=name,
                defaults={'description': fake.text(max_nb_chars=100), 'sub_categories': [{'name': f'Général {name}'}]}
            )
            categories.append(cat)
        self.stdout.write(self.style.SUCCESS(f"Created {len(categories)} categories."))

        # 2. Create Job Offers (~50)
        jobs = []
        statuses = ['published', 'draft', 'archived']
        
        for i in range(50):
            cat = random.choice(categories)
            job = JobOffer.objects.create(
                title=fake.job(),
                description=fake.paragraphs(nb=3, ext_word_list=None),
                category=cat,
                company_name=fake.company(),
                company_website_address=fake.url(),
                company_location=fake.city(),
                contact="+226" + str(random.randint(50000000, 79999999)),
                status=random.choices(statuses, weights=[0.8, 0.1, 0.1])[0],
                created_at=fake.date_time_between(start_date='-60d', end_date='now', tzinfo=timezone.get_current_timezone())
            )
            jobs.append(job)
        self.stdout.write(self.style.SUCCESS(f"Created {len(jobs)} jobs."))

        # 3. Create Users & Subscriptions (~200)
        users = []
        now = timezone.now()
        
        for i in range(210):
            # Generate a Burkina Faso style number (+226 followed by 8 digits)
            phone = "+226" + str(random.randint(50000000, 79999999))
            join_date = fake.date_time_between(start_date='-90d', end_date='now', tzinfo=timezone.get_current_timezone())
            
            user, created = User.objects.get_or_create(phone_number=phone)
            if created:
                user.date_joined = join_date
                user.sms_notification_active = random.choices([True, False], weights=[0.8, 0.2])[0]
                user.save()
            users.append(user)

            # Assign 1 to 3 random subscriptions
            user_cats = random.sample(categories, random.randint(1, 4))
            for cat in user_cats:
                sub, _ = Subscription.objects.get_or_create(
                    user=user, category=cat,
                    defaults={
                        'subscribed_via': random.choice(['WEB', 'USSD', 'ADMIN']),
                        'is_active': user.sms_notification_active
                    }
                )
                if created:
                    sub.subscribed_at = join_date + timedelta(hours=random.randint(1, 48))
                    sub.save()
        self.stdout.write(self.style.SUCCESS(f"Created {len(users)} users and their subscriptions."))

        # 4. Create Contact Messages (~20)
        for i in range(20):
            ContactMessage.objects.create(
                full_name=fake.name(),
                email=fake.email(),
                number="+226" + str(random.randint(50000000, 79999999)),
                subject=fake.sentence(nb_words=6),
                message=fake.text(),
                created_at=fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.get_current_timezone())
            )
        self.stdout.write(self.style.SUCCESS("Created 20 contact messages."))

        # 5. Create Blacklists (~5)
        for i in range(5):
            Blacklist.objects.get_or_create(
                phone_number="+226" + str(random.randint(50000000, 79999999)),
                defaults={'reason': fake.sentence()}
            )

        # 6. Create SMS Delivery Logs (~300 over the last 7 days)
        sms_logs_count = 0
        for i in range(300):
            random_user = random.choice(users)
            random_job = random.choice(jobs)
            # Sent in the last 7 days to populate the dashboard stats
            sent_time = fake.date_time_between(start_date='-7d', end_date='now', tzinfo=timezone.get_current_timezone())
            
            SMSDeliveryLog.objects.create(
                phone_number=random_user.phone_number,
                message_content=f"New Job: {random_job.title} at {random_job.company_name}",
                status=random.choices(['SENT', 'FAILED'], weights=[0.85, 0.15])[0],
                sent_at=sent_time
            )
            sms_logs_count += 1
            
        self.stdout.write(self.style.SUCCESS(f"Created {sms_logs_count} SMS logs."))
        self.stdout.write(self.style.SUCCESS("Fake data generation complete!"))
