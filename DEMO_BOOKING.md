# Advoxy Demo Booking Mode

Demo booking tools are development/test only. They are enabled when Django `DEBUG=1` or `DEMO_BOOKING_TOOLS_ENABLED=true`; they are blocked for non-admin users and refuse live Stripe keys in development.

## 1. Seed Demo Data

From the repository root:

```powershell
py -3.11 backend\manage.py seed_demo_data
```

This creates Calgary demo data for:

- customer: `demo_customer_01@demo.advoxy.test`
- professional: `demo_professional_02@demo.advoxy.test`
- admin: `demo_admin@demo.advoxy.test`
- password for all demo accounts: `DemoOnly-Advoxy-2026!`
- Hair > Men > Men's Haircut
- verified, online professionals
- professional services, prices, availability, notifications, reviews, and sample lifecycle data

To remove only demo-marked data:

```powershell
py -3.11 backend\manage.py seed_demo_data --reset
```

## 2. Configure Stripe Test Mode

Use Stripe test keys only:

```env
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

Use Stripe's test card in the checkout UI:

```text
4242 4242 4242 4242
Any future expiry
Any 3-digit CVC
Any postal code
```

## 3. Run The App

```powershell
py -3.11 backend\manage.py runserver 127.0.0.1:8000
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## 4. Customer Demo Flow

1. On the homepage, search:
   - Location: `Calgary`
   - Category: `Hair`
   - Audience: `Men`
   - Service: `Men's Haircut`
   - Booking type: scheduled or instant
2. Open a matching professional card.
3. Continue to booking.
4. Log in or sign up with `demo_customer_01@demo.advoxy.test`.
5. Authorize payment with the Stripe test card.
6. The booking is now ready for lifecycle simulation.

## 5. Admin Demo Simulation API

Log in as `demo_admin@demo.advoxy.test`, then use the admin token against these development-only endpoints.

Scenario lookup:

```http
GET /api/demo/scenario/
```

Professional controls:

```http
POST /api/demo/professionals/{professional_id}/online/
POST /api/demo/professionals/{professional_id}/availability/
```

Booking lifecycle:

```http
POST /api/demo/bookings/{booking_id}/match/
POST /api/demo/bookings/{booking_id}/accept/
POST /api/demo/bookings/{booking_id}/decline/        {"reason":"Demo decline reason"}
POST /api/demo/bookings/{booking_id}/left/
POST /api/demo/bookings/{booking_id}/arrival-eligibility/
POST /api/demo/bookings/{booking_id}/reached/
POST /api/demo/bookings/{booking_id}/started/
POST /api/demo/bookings/{booking_id}/completed/
POST /api/demo/bookings/{booking_id}/confirm-complete/
POST /api/demo/bookings/{booking_id}/review/         {"rating":5,"comment":"Great demo service."}
```

`confirm-complete` calls the Stripe capture service. It does not directly flip payment rows to captured.
