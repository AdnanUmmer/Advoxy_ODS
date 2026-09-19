from datetime import date, timedelta
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from accounts.models import Address, ProfessionalProfile, User
from bookings.models import (
    AvailabilitySlot,
    Booking,
    BookingDecline,
    BookingNotification,
    BookingService,
    BookingStatusEvent,
)
from catalog.models import (
    Category,
    MarketplaceSettings,
    MarketplaceSettingsAudit,
    ProfessionalService,
    Service,
    SubCategory,
)
from messaging.models import Conversation, Message
from payments.models import PaymentAuthorization, Payout
from reviews.models import Review
from verification.models import ProfessionalVerification


class Command(BaseCommand):
    help = "Seed deterministic synthetic Advoxy marketplace data for development/staging."

    DEMO_PASSWORD = "DemoOnly-Advoxy-2026!"
    DEMO_EMAIL_DOMAIN = "demo.advoxy.test"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove only records marked is_demo=True and do not seed new data.",
        )

    def handle(self, *args, **options):
        self._ensure_demo_seed_allowed()
        with transaction.atomic():
            if options["reset"]:
                counts = self._reset_demo_data()
                self.stdout.write(self.style.SUCCESS(f"Removed demo data: {counts}"))
                return

            self._clear_demo_transactions()
            catalog = self._seed_catalog()
            users = self._seed_users()
            professionals = self._seed_professionals(users["professionals"], catalog)
            self._seed_verification(professionals)
            self._seed_bookings(users["customers"], professionals)
            self._seed_reviews()
            self._seed_chat()
            self._seed_demo_audit(users["admin"])

        self._write_summary(users, professionals)

    def _seed_catalog(self):
        categories = {}
        for name, slug in (("Hair", "hair"), ("Nails", "nails")):
            category, created = Category.objects.get_or_create(slug=slug, defaults={"name": name})
            category.name = name
            category.is_active = True
            if created:
                category.is_demo = True
            category.save(update_fields=["name", "is_active", "is_demo"])
            categories[slug] = category

        specs = {
            "mens-hair": (categories["hair"], "Men", SubCategory.Audience.MEN, [
                ("Men's Haircut", "mens-haircut", "Wash, cut, and professional finish.", 45, 40),
                ("Fade", "fade", "Precision fade with a tailored finish.", 45, 42),
                ("Taper", "taper", "Classic taper with detailed edging.", 40, 38),
                ("Buzz Cut", "buzz-cut", "Clean, low-maintenance clipper cut.", 30, 30),
                ("Beard Trim", "beard-trim", "Shape and finish for a polished beard.", 30, 28),
                ("Hair & Beard Combo", "hair-beard-combo", "Haircut and beard trim in one visit.", 75, 62),
            ]),
            "womens-hair": (categories["hair"], "Women", SubCategory.Audience.WOMEN, [
                ("Women's Haircut", "womens-haircut", "A tailored cut, wash, and finish.", 60, 65),
                ("Hair Styling", "hair-styling", "Polished styling for an everyday or event look.", 60, 75),
                ("Blow Dry", "blow-dry", "Professional blow dry and finish.", 45, 55),
                ("Hair Straightening", "hair-straightening", "Smooth, straight finish with heat protection.", 90, 110),
                ("Hair Curling", "hair-curling", "Soft curls or defined waves.", 75, 95),
                ("Updo", "updo", "Event-ready updo styling.", 90, 125),
                ("Braids", "braids", "Protective and occasion braid styling.", 90, 100),
                ("Hair Treatment", "hair-treatment", "Conditioning treatment and restorative finish.", 60, 80),
            ]),
            "kids-hair": (categories["hair"], "Kids", SubCategory.Audience.KIDS, [
                ("Kids Haircut", "kids-haircut", "Patient, family-friendly haircut.", 40, 35),
                ("Kids Styling", "kids-styling", "Simple styling for special occasions.", 45, 40),
                ("Kids Hair & Wash", "kids-hair-wash", "Wash, trim, and gentle finish.", 50, 45),
            ]),
            "manicure": (categories["nails"], "Manicure", SubCategory.Audience.UNISEX, [
                ("Classic Manicure", "classic-manicure", "Shape, cuticle care, and classic polish.", 60, 45),
                ("Gel Manicure", "gel-manicure", "Long-wear gel manicure and finish.", 75, 60),
                ("French Manicure", "french-manicure", "Classic French finish with clean detail.", 75, 65),
                ("Manicure + Gel", "manicure-gel", "Full manicure with gel polish.", 90, 70),
            ]),
            "pedicure": (categories["nails"], "Pedicure", SubCategory.Audience.UNISEX, [
                ("Classic Pedicure", "classic-pedicure", "Shape, care, and classic polish.", 60, 55),
                ("Gel Pedicure", "gel-pedicure", "Pedicure with long-wear gel finish.", 75, 70),
                ("Spa Pedicure", "spa-pedicure", "Soak, exfoliation, massage, and polish.", 90, 85),
                ("French Pedicure", "french-pedicure", "Pedicure with a French finish.", 75, 70),
            ]),
            "nail-art": (categories["nails"], "Nail Art", SubCategory.Audience.UNISEX, [
                ("French Tips", "french-tips", "Detailed French tip design.", 60, 55),
                ("Minimal Nail Art", "minimal-nail-art", "Subtle, modern accent details.", 60, 60),
                ("Chrome", "chrome", "Reflective chrome finish.", 75, 65),
                ("Ombre", "ombre", "Blended ombre nail design.", 90, 80),
                ("Custom Nail Art", "custom-nail-art", "Custom design consultation and execution.", 120, 110),
            ]),
            "nail-extensions": (categories["nails"], "Nail Extensions", SubCategory.Audience.UNISEX, [
                ("Gel Extensions", "gel-extensions", "Structured gel extensions and finish.", 120, 105),
                ("Acrylic Extensions", "acrylic-extensions", "Acrylic extensions with shaping.", 135, 115),
                ("Gel Overlay", "gel-overlay", "Strengthening gel overlay.", 90, 85),
                ("Acrylic Overlay", "acrylic-overlay", "Strengthening acrylic overlay.", 90, 85),
            ]),
        }
        services = {}
        for order, (sub_slug, (category, name, audience, service_specs)) in enumerate(specs.items(), 1):
            subcategory, created = SubCategory.objects.get_or_create(
                category=category,
                slug=sub_slug,
                defaults={"name": name, "audience": audience, "display_order": order},
            )
            subcategory.name = name
            subcategory.audience = audience
            subcategory.display_order = order
            if created:
                subcategory.is_demo = True
            subcategory.save(update_fields=["name", "audience", "display_order", "is_demo"])
            for display_order, (service_name, slug, description, duration, price) in enumerate(service_specs, 1):
                service = Service.objects.filter(slug=slug).first()
                if service is None:
                    service = Service.objects.filter(name__iexact=service_name).first()
                if service is None:
                    service = Service.objects.create(
                        subcategory=subcategory,
                        name=service_name,
                        slug=slug,
                        description=description,
                        duration_minutes=duration,
                        default_price=Decimal(str(price)),
                        display_order=display_order,
                        is_active=True,
                        is_demo=True,
                    )
                else:
                    service.subcategory = subcategory
                    service.name = service_name
                    service.slug = slug
                    service.description = description
                    service.duration_minutes = duration
                    service.default_price = Decimal(str(price))
                    service.display_order = display_order
                    service.is_active = True
                    service.save(update_fields=[
                        "subcategory", "name", "slug", "description", "duration_minutes",
                        "default_price", "display_order", "is_active",
                    ])
                services[slug] = service
        return services

    def _seed_users(self):
        customers = []
        for index in range(1, 21):
            user = self._user(
                f"demo_customer_{index:02d}",
                f"Customer{index:02d}",
                "Demo",
                User.Role.CUSTOMER,
            )
            self._address(user, "Home", index)
            customers.append(user)

        professionals = []
        for index in range(1, 13):
            first_name, last_name = self.PROFESSIONAL_NAMES[index - 1]
            professionals.append(self._user(
                f"demo_professional_{index:02d}", first_name, last_name, User.Role.PROFESSIONAL
            ))

        admin = self._user("demo_admin", "Demo", "Administrator", User.Role.ADMIN)
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])
        return {"customers": customers, "professionals": professionals, "admin": admin}

    PROFESSIONAL_NAMES = [
        ("Maya", "Laurent"), ("Noa", "Bell"), ("Elena", "Rossi"), ("Sofia", "Adeyemi"),
        ("Daniel", "Carter"), ("Priya", "Shah"), ("Jonah", "Mercer"), ("Amara", "Okafor"),
        ("Theo", "Nguyen"), ("Lina", "Petrov"), ("Morgan", "Reed"), ("Avery", "Chen"),
    ]

    PROFESSIONAL_COORDINATES = [
        (51.0452, -114.0698), (51.0520, -114.0830), (51.0370, -114.0620),
        (51.0800, -114.0450), (51.0150, -114.1000), (51.0950, -114.1200),
        (50.9900, -114.0300), (51.1300, -114.1800), (50.9500, -114.0000),
        (51.1800, -114.2200), (50.9200, -114.1600), (51.2200, -114.2600),
    ]

    ASSIGNMENTS = [
        ["womens-haircut", "hair-styling", "blow-dry", "updo"],
        ["mens-haircut", "fade", "taper", "beard-trim"],
        ["classic-manicure", "gel-manicure", "french-manicure", "custom-nail-art"],
        ["classic-pedicure", "spa-pedicure", "gel-pedicure", "french-pedicure"],
        ["mens-haircut", "hair-styling", "classic-manicure", "classic-pedicure"],
        ["hair-straightening", "hair-curling", "braids", "hair-treatment"],
        ["kids-haircut", "kids-styling", "kids-hair-wash", "mens-haircut"],
        ["gel-extensions", "acrylic-extensions", "gel-overlay", "custom-nail-art"],
        ["fade", "buzz-cut", "hair-beard-combo", "beard-trim"],
        ["womens-haircut", "blow-dry", "braids", "gel-manicure"],
        ["classic-manicure", "manicure-gel", "chrome", "ombre"],
        ["classic-pedicure", "spa-pedicure", "custom-nail-art", "acrylic-overlay"],
    ]

    def _user(self, username, first_name, last_name, role):
        email = f"{username}@{self.DEMO_EMAIL_DOMAIN}"
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.filter(email=email).first()
        if user is None:
            user = User(username=email, email=email, role=role, is_demo=True)
        user.username = email
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.date_of_birth = date(1990, 1, 1)
        user.is_demo = True
        user.set_password(self.DEMO_PASSWORD)
        user.save()
        return user

    def _address(self, user, label, index):
        latitude, longitude = self._customer_coordinate(index)
        return Address.objects.update_or_create(
            user=user,
            label=label,
            defaults={
                "full_address": f"Demo {label}, Calgary, AB",
                "latitude": Decimal(str(latitude)),
                "longitude": Decimal(str(longitude)),
                "is_default": True,
                "is_demo": True,
            },
        )[0]

    def _seed_professionals(self, users, services):
        profiles = []
        for index, user in enumerate(users):
            latitude, longitude = self.PROFESSIONAL_COORDINATES[index]
            address = Address.objects.update_or_create(
                user=user,
                label="Demo Studio",
                defaults={
                    "full_address": f"Demo Studio {index + 1}, Calgary, AB",
                    "latitude": Decimal(str(latitude)),
                    "longitude": Decimal(str(longitude)),
                    "is_default": True,
                    "is_demo": True,
                },
            )[0]
            profile, _ = ProfessionalProfile.objects.update_or_create(
                user=user,
                defaults={
                    "bio": f"Synthetic demo professional specializing in {self.ASSIGNMENTS[index][0].replace('-', ' ')} and serving Calgary clients.",
                    "years_experience": 4 + index,
                    "service_radius_km": Decimal("25.0"),
                    "free_travel_radius_km": Decimal("5.0"),
                    "per_km_travel_fee": Decimal("2.00"),
                    "is_online": index % 3 != 2,
                    "is_active": True,
                    "base_address": address,
                    "service_cities": ["Calgary"],
                    "is_demo": True,
                },
            )
            profiles.append(profile)
            for service_index, slug in enumerate(self.ASSIGNMENTS[index]):
                service = services[slug]
                price = service.default_price + Decimal(str((index % 4) * 5 + service_index * 2))
                ProfessionalService.objects.update_or_create(
                    professional=profile,
                    service=service,
                    defaults={
                        "price": price,
                        "duration_minutes": service.duration_minutes,
                        "is_active": True,
                        "is_demo": True,
                    },
                )
        return profiles

    def _seed_verification(self, profiles):
        for index, profile in enumerate(profiles, 1):
            ProfessionalVerification.objects.update_or_create(
                professional=profile,
                defaults={
                    "provider": ProfessionalVerification.Provider.PERSONA,
                    "provider_reference_id": f"DEMO_VERIFICATION_{index:02d}",
                    "status": ProfessionalVerification.Status.APPROVED,
                    "fee_paid": True,
                    "identity_check_passed": True,
                    "criminal_record_check_passed": True,
                    "decided_at": timezone.now(),
                    "expires_at": timezone.now() + timedelta(days=365),
                    "is_demo": True,
                },
            )

    def _seed_bookings(self, customers, profiles):
        marketplace = MarketplaceSettings.current()
        service_rows = [
            list(ProfessionalService.objects.filter(professional=profile, is_demo=True).select_related("service"))
            for profile in profiles
        ]
        now = timezone.now()
        for index in range(84):
            profile_index = index % len(profiles)
            profile = profiles[profile_index]
            customer = customers[index % len(customers)]
            primary = service_rows[profile_index][index % len(service_rows[profile_index])]
            selected = [primary]
            if index % 5 == 0:
                selected.append(service_rows[profile_index][(index + 1) % len(service_rows[profile_index])])
            duration = sum(item.duration_minutes for item in selected)
            address = Address.objects.filter(user=customer, is_demo=True).first()
            booking_type = Booking.BookingType.INSTANT if index >= 72 else Booking.BookingType.SCHEDULED
            scheduled_time = None
            if booking_type == Booking.BookingType.SCHEDULED:
                day_offsets = [-28, -21, -14, -7, 3, 10]
                day_offset = day_offsets[index // len(profiles)]
                scheduled_time = (now + timedelta(days=day_offset)).replace(
                    hour=9 + (profile_index % 5), minute=0, second=0, microsecond=0
                )
            distance = self._distance_km(address, profile.base_address)
            travel_fee = Decimal("0.00")
            if marketplace.travel_fees_enabled:
                excess_distance = Decimal(str(max(0, distance - float(marketplace.included_travel_distance_km))))
                travel_fee = min(
                    excess_distance * Decimal(str(marketplace.travel_fee_per_km)),
                    Decimal(str(marketplace.maximum_travel_fee)),
                ).quantize(Decimal("0.01"))
            service_price = sum((item.price for item in selected), Decimal("0.00"))
            commission = (service_price * marketplace.commission_percent / Decimal("100")) + marketplace.fixed_platform_fee
            commission = max(commission, marketplace.minimum_platform_fee)
            if marketplace.maximum_platform_fee:
                commission = min(commission, marketplace.maximum_platform_fee)
            commission = commission.quantize(Decimal("0.01"))
            final_status, event_chain = self._booking_state(index, booking_type)
            slot = None
            if booking_type == Booking.BookingType.SCHEDULED:
                slot = AvailabilitySlot.objects.create(
                    professional=profile,
                    start_time=scheduled_time,
                    end_time=scheduled_time + timedelta(minutes=max(180, duration)),
                    is_booked=final_status not in {Booking.Status.CANCELLED_CUSTOMER, Booking.Status.CANCELLED_PROFESSIONAL},
                    is_demo=True,
                )
            booking = Booking.objects.create(
                customer=customer,
                professional=profile,
                professional_service=primary,
                availability_slot=slot,
                address=address,
                booking_type=booking_type,
                status=final_status,
                service_price=service_price,
                duration_minutes=duration,
                travel_fee=travel_fee,
                priority_fee=Decimal("15.00") if booking_type == Booking.BookingType.INSTANT else Decimal("0.00"),
                platform_commission=commission,
                scheduled_time=scheduled_time,
                reached_latitude=address.latitude if len(event_chain) >= 4 else None,
                reached_longitude=address.longitude if len(event_chain) >= 4 else None,
                left_at=scheduled_time if len(event_chain) >= 3 else None,
                reached_at=scheduled_time if len(event_chain) >= 4 else None,
                started_at=scheduled_time if len(event_chain) >= 5 else None,
                completed_at=scheduled_time if len(event_chain) >= 6 else None,
                confirmed_complete_at=scheduled_time if final_status == Booking.Status.CONFIRMED_COMPLETE else None,
                is_demo=True,
            )
            for service in selected:
                BookingService.objects.create(
                    booking=booking,
                    professional_service=service,
                    service_price=service.price,
                    duration_minutes=service.duration_minutes,
                )
            for status_value in event_chain:
                BookingStatusEvent.objects.create(
                    booking=booking,
                    status=status_value,
                    note="Synthetic demo lifecycle event.",
                )
            if final_status == Booking.Status.CANCELLED_PROFESSIONAL:
                BookingDecline.objects.create(
                    booking=booking,
                    professional=profile,
                    reason="Synthetic demo decline for workflow coverage.",
                )
            self._seed_payment(booking, index)
            self._seed_notifications(booking, event_chain)

    def _booking_state(self, index, booking_type):
        if booking_type == Booking.BookingType.INSTANT:
            status = Booking.Status.CONFIRMED if index % 2 else Booking.Status.PENDING_ACCEPT
            return status, [Booking.Status.PENDING_ACCEPT, status]
        if index < 40:
            return Booking.Status.CONFIRMED_COMPLETE, [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.LEFT, Booking.Status.REACHED, Booking.Status.STARTED, Booking.Status.COMPLETED, Booking.Status.CONFIRMED_COMPLETE]
        if index < 46:
            return Booking.Status.COMPLETED, [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.LEFT, Booking.Status.REACHED, Booking.Status.STARTED, Booking.Status.COMPLETED]
        if index < 52:
            return Booking.Status.STARTED, [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.LEFT, Booking.Status.REACHED, Booking.Status.STARTED]
        if index < 58:
            return Booking.Status.REACHED, [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED, Booking.Status.LEFT, Booking.Status.REACHED]
        if index < 64:
            return Booking.Status.CANCELLED_CUSTOMER, [Booking.Status.PENDING_ACCEPT, Booking.Status.CANCELLED_CUSTOMER]
        if index < 70:
            return Booking.Status.CANCELLED_PROFESSIONAL, [Booking.Status.PENDING_ACCEPT, Booking.Status.CANCELLED_PROFESSIONAL]
        if index < 72:
            return Booking.Status.CONFIRMED, [Booking.Status.PENDING_ACCEPT, Booking.Status.CONFIRMED]
        return Booking.Status.PENDING_ACCEPT, [Booking.Status.PENDING_ACCEPT]

    def _seed_payment(self, booking, index):
        if booking.status == Booking.Status.CONFIRMED_COMPLETE:
            status_value = PaymentAuthorization.Status.CAPTURED
        elif booking.status == Booking.Status.CANCELLED_CUSTOMER:
            status_value = PaymentAuthorization.Status.REFUNDED
        elif booking.status == Booking.Status.CANCELLED_PROFESSIONAL:
            status_value = PaymentAuthorization.Status.CANCELLED
        else:
            status_value = PaymentAuthorization.Status.AUTHORIZED
        PaymentAuthorization.objects.create(
            booking=booking,
            stripe_payment_intent_id=f"DEMO_PAYMENT_{index + 1:04d}",
            provider=PaymentAuthorization.Provider.DEMO,
            amount=booking.total_amount,
            status=status_value,
            captured_at=timezone.now() if status_value in {PaymentAuthorization.Status.CAPTURED, PaymentAuthorization.Status.REFUNDED} else None,
            refunded_at=timezone.now() if status_value == PaymentAuthorization.Status.REFUNDED else None,
            admin_note="Synthetic demo payment; no external provider transaction.",
            is_demo=True,
        )
        if status_value in {PaymentAuthorization.Status.CAPTURED, PaymentAuthorization.Status.REFUNDED}:
            Payout.objects.create(
                booking=booking,
                professional=booking.professional,
                gross_amount=booking.service_price + booking.travel_fee,
                commission_amount=booking.platform_commission,
                net_amount=booking.service_price + booking.travel_fee - booking.platform_commission,
                status=Payout.Status.PENDING,
                dispute_window_ends_at=timezone.now() + timedelta(days=7),
                is_demo=True,
            )

    def _seed_notifications(self, booking, event_chain):
        events = [(value, f"Demo update: booking is {value.lower().replace('_', ' ')}.") for value in event_chain]
        events.append(("REVIEW_REQUEST", "Demo reminder: share feedback after your appointment."))
        for event, body in events:
            BookingNotification.objects.create(
                booking=booking,
                recipient=booking.customer,
                event=event,
                body=body,
                is_demo=True,
            )

    def _seed_reviews(self):
        ratings = [5, 5, 4, 5, 3, 4, 5, 5, 4, 5]
        completed = list(Booking.objects.filter(is_demo=True, status=Booking.Status.CONFIRMED_COMPLETE).order_by("id"))
        for index, booking in enumerate(completed[:40]):
            Review.objects.create(
                booking=booking,
                reviewer=booking.customer,
                reviewee=booking.professional.user,
                rating=ratings[index % len(ratings)],
                comment="Synthetic demo review for marketplace presentation.",
                is_demo=True,
            )
        for profile in ProfessionalProfile.objects.filter(is_demo=True):
            reviews = Review.objects.filter(reviewee=profile.user)
            profile.review_count = reviews.count()
            profile.average_rating = reviews.aggregate(average=Avg("rating"))["average"]
            profile.save(update_fields=["review_count", "average_rating"])

    def _seed_chat(self):
        bodies = [
            "Hi, I am looking forward to the appointment.",
            "Thanks, I have your location details.",
            "I will bring the requested demo service supplies.",
            "Great, see you soon.",
        ]
        for booking in Booking.objects.filter(is_demo=True).order_by("id")[:15]:
            conversation = Conversation.objects.create(booking=booking, is_demo=True)
            participants = [booking.customer, booking.professional.user]
            for message_index, body in enumerate(bodies):
                Message.objects.create(
                    conversation=conversation,
                    sender=participants[message_index % 2],
                    body=body,
                    read_at=timezone.now() if message_index < 2 else None,
                    is_demo=True,
                )

    def _seed_demo_audit(self, admin):
        MarketplaceSettingsAudit.objects.create(
            settings=MarketplaceSettings.current(),
            admin=admin,
            changes={"demo_seed": "Synthetic marketplace configuration activity"},
            reason="Demo seed activity",
            is_demo=True,
        )

    def _clear_demo_transactions(self):
        PaymentAuthorization.objects.filter(is_demo=True).delete()
        Payout.objects.filter(is_demo=True).delete()
        Review.objects.filter(is_demo=True).delete()
        Message.objects.filter(is_demo=True).delete()
        Conversation.objects.filter(is_demo=True).delete()
        BookingNotification.objects.filter(is_demo=True).delete()
        Booking.objects.filter(is_demo=True).delete()
        AvailabilitySlot.objects.filter(is_demo=True).delete()
        MarketplaceSettingsAudit.objects.filter(is_demo=True).delete()

    def _reset_demo_data(self):
        self._clear_demo_transactions()
        ProfessionalVerification.objects.filter(is_demo=True).delete()
        ProfessionalService.objects.filter(is_demo=True).delete()
        ProfessionalProfile.objects.filter(is_demo=True).delete()
        Address.objects.filter(is_demo=True).delete()
        User.objects.filter(is_demo=True).delete()
        Service.objects.filter(is_demo=True).exclude(offered_by__is_demo=False).delete()
        SubCategory.objects.filter(is_demo=True).exclude(services__is_demo=False).delete()
        Category.objects.filter(is_demo=True).exclude(subcategories__is_demo=False).delete()
        return {
            "users_remaining": User.objects.filter(is_demo=True).count(),
            "services_remaining": Service.objects.filter(is_demo=True).count(),
        }

    def _distance_km(self, first, second):
        latitude_delta = radians(float(second.latitude) - float(first.latitude))
        longitude_delta = radians(float(second.longitude) - float(first.longitude))
        first_latitude = radians(float(first.latitude))
        second_latitude = radians(float(second.latitude))
        value = sin(latitude_delta / 2) ** 2 + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
        return 6371 * 2 * asin(sqrt(value))

    def _customer_coordinate(self, index):
        center_latitude, center_longitude = 51.0447, -114.0719
        offsets = [(0.005, 0.004), (-0.012, 0.008), (0.020, -0.015), (-0.030, -0.020), (0.045, 0.030)]
        latitude_offset, longitude_offset = offsets[(index - 1) % len(offsets)]
        multiplier = 1 + ((index - 1) // len(offsets)) * 0.7
        return center_latitude + latitude_offset * multiplier, center_longitude + longitude_offset * multiplier

    def _write_summary(self, users, professionals):
        status_counts = {
            status: Booking.objects.filter(is_demo=True, status=status).count()
            for status, _ in Booking.Status.choices
            if Booking.objects.filter(is_demo=True, status=status).exists()
        }
        self.stdout.write(self.style.SUCCESS("Seeded synthetic Advoxy demo data."))
        self.stdout.write(f"Demo login password: {self.DEMO_PASSWORD} (development/staging only)")
        self.stdout.write(f"Customers: {len(users['customers'])}")
        self.stdout.write(f"Professionals: {len(professionals)}")
        self.stdout.write(f"Services: {Service.objects.filter(is_active=True).count()}")
        self.stdout.write(f"Professional-service relationships: {ProfessionalService.objects.filter(is_demo=True).count()}")
        self.stdout.write(f"Availability records: {AvailabilitySlot.objects.filter(is_demo=True).count()}")
        self.stdout.write(f"Bookings by status: {status_counts}")
        self.stdout.write(f"Payments: {PaymentAuthorization.objects.filter(is_demo=True).count()}")
        self.stdout.write(f"Reviews: {Review.objects.filter(is_demo=True).count()}")
        self.stdout.write(f"Notifications: {BookingNotification.objects.filter(is_demo=True).count()}")
        self.stdout.write(f"Chat messages: {Message.objects.filter(is_demo=True).count()}")

    def _ensure_demo_seed_allowed(self):
        if not settings.DEMO_BOOKING_TOOLS_ENABLED:
            raise CommandError("Demo seed data is disabled. Enable DEBUG or DEMO_BOOKING_TOOLS_ENABLED only in development/test.")
        if not settings.DEBUG and not settings.DATABASES["default"]["NAME"]:
            raise CommandError("Demo seed data refused outside a development/test database.")
        if settings.STRIPE_SECRET_KEY.startswith("sk_live_"):
            raise CommandError("Demo seed data refused while a live Stripe secret key is configured.")
