# Advoxy Live Production-Readiness TODO

Last updated: 2026-09-07

Status legend:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done / locally verified
- `[!]` Blocked or credential-dependent

## 0. Working Notes

- `[x]` Repository located at `C:\Users\10adn\Downloads\advoxy`.
- `[x]` Frontend located at `frontend`.
- `[x]` Backend located at `backend`.
- `[x]` No `.git` directory found at repository root during initial check.
- `[~]` Production-readiness audit is active.
- `[x]` Frontend lint passes.
- `[x]` Frontend production build passes.
- `[x]` Backend Django check passes with no issues.
- `[x]` Backend migrations apply on local SQLite.
- `[x]` Backend test suite passes: 24 tests.

## Current High-Priority Findings

- `[x]` Fixed frontend build failure caused by duplicate `email` in signup API payload.
- `[x]` Fixed frontend lint blocker in `HeroSearch`.
- `[x]` Added missing `/services` route so navigation no longer points at a missing page.
- `[x]` Replaced dead Terms/Privacy signup links with real routes.
- `[x]` Added `django-allauth` to backend requirements because settings depend on it.
- `[x]` Wired allauth URLs and current allauth settings for Google OAuth provider boundary.
- `[x]` Tightened public professional profile serialization so nested user email, phone, and addresses are not exposed publicly.
- `[!]` A Firebase service-account JSON with a private key exists under `backend/`. Delete/revoke it before production and use `FIREBASE_CREDENTIALS_JSON` with a private deployment secret path.
- `[!]` `backend\.env` exists locally. It was not read or printed; keep it out of source control.
- `[!]` Legal Terms/Privacy pages now exist but contain launch-blocking legal placeholder copy that needs counsel-approved text.
- `[!]` Twilio voice call task remains credential/integration-dependent.
- `[!]` Proposal expects professionals to operate exclusively through the mobile app, but this repo includes professional web routes such as `/vendor`; audit whether these should be admin/internal support only, removed from public nav, or preserved as a temporary web management surface.
- `[!]` Verification app currently has models/admin but no DRF submission/status/webhook workflow for Persona or Certn.
- `[!]` Messaging is protected by booking participants, but it is database-backed polling only; Firebase/Stream real-time chat is not implemented.
- `[x]` Mutual review model exists and 1- or 2-star reviews are auto-flagged for admin review.
- `[!]` Scheduled reaffirmation Celery tasks exist, but Firebase/Twilio notification delivery and automated call handling remain stubbed.

## Proposal Context Extracted From PDF

- `[x]` Proposal reviewed: `On-Demand_Services_PROJECT_PROPOSAL-1.pdf`, 12 pages.
- `[ ]` Website must support full customer booking: browse, book, pay, chat, and masked calling.
- `[ ]` Mobile app must support customer and professional roles; professionals are mobile-only in the proposal.
- `[ ]` Admin dashboard is website-only.
- `[ ]` Launch market is Calgary, Alberta, with expansion-ready architecture.
- `[ ]` Visitors should be able to search/location-check availability before signup.
- `[ ]` Customer categories should be Hair and Nails, with subcategories/services from backend catalog.
- `[ ]` Instant booking should add a fixed priority charge and match nearest online available professional by expanding radius.
- `[ ]` Scheduled booking should use real availability slots and a 10-minute professional accept window.
- `[ ]` Declines must require a reason, show it to the customer, and rematch to the next best professional.
- `[ ]` Payment flow must authorize at booking and capture only after customer-confirmed completion.
- `[ ]` Customer/professional notifications must fire at booking confirmed, left, reached, started, completed, and payment events.
- `[~]` Reaffirmation is required 1 hour before scheduled bookings, with 3 reminders and a follow-up automated call if needed.
- `[ ]` Reached status must be GPS-verified against the saved customer address.
- `[ ]` Professional verification must store provider outcome/reference/status only, not raw government ID documents.
- `[ ]` Before/after photo workflow must require explicit customer consent.
- `[x]` Reviews are mutual: customer reviews professional and professional can review customer.
- `[ ]` Admin must handle verifications, live bookings, commissions, cancellations, complaints/disputes/refunds, categories, analytics, banners/notifications, and platform settings.
- `[ ]` 1- or 2-star reviews should automatically flag/call out for admin review.
- `[ ]` Integrations expected by proposal: Stripe, Stripe Connect, Google Maps, Firebase push/chat, Twilio Proxy/calling, Twilio SMS, SendGrid/email, Cloudinary, Certn or Persona.
- `[!]` Legal/regulatory/compliance items remain client/counsel-dependent: Calgary licensing, Alberta PIPA, call recording notice/consent, background-check level, insurance, worker classification, hygiene standards, consumer protection, and taxes.

## 1. Repository Audit

- `[x]` Read root `README.md`.
- `[x]` Read frontend `package.json`, Next config, TypeScript config, lint config.
- `[x]` Read backend `requirements.txt`, Django settings, root URL config.
- `[~]` Inventory Django apps, models, serializers, views, permissions, URLs, migrations, admin, and tests.
- `[~]` Inventory frontend routes, components, API client, auth flow, protected pages, and styling.
- `[x]` Search for TODO/FIXME/mock/dummy/placeholder/fake/hardcoded URLs/secrets/dead links/unsafe permissions.
- `[x]` Build severity-ordered issue list.

## 2. Backend

- `[x]` Validate Django settings for development and production.
- `[~]` Validate environment variable handling and `.env.example`.
- `[ ]` Validate PostgreSQL-ready database configuration.
- `[x]` Validate migrations from scratch.
- `[ ]` Fix model constraints, indexes, and relationships where needed.
- `[x]` Fix serializer validation and sensitive field exposure.
- `[ ]` Fix object-level permissions and role-aware access.
- `[ ]` Add pagination/filtering/sorting where needed.
- `[ ]` Fix N+1 query risks with `select_related` / `prefetch_related`.

## 3. Booking System

- `[x]` Audit booking lifecycle states and transitions.
- `[x]` Prevent arbitrary status mutation.
- `[~]` Enforce customer/professional/admin role rules.
- `[~]` Add transaction-safe conflict prevention.
- `[~]` Validate services, service areas, timing, and duration.
- `[ ]` Add or repair booking tests.

## 4. Frontend

- `[~]` Audit all routes/pages for broken UI, dead buttons, and inconsistent styling.
- `[~]` Complete homepage hero search: service, location, and when controls.
- `[x]` Ensure Explore Professionals navigates to real backend-driven results.
- `[ ]` Ensure Hair and Nails category flows are real and consistent.
- `[~]` Ensure instant and scheduled View All buttons work.
- `[x]` Ensure professional cards open real profile pages.
- `[ ]` Add loading, error, and empty states for data-driven views.
- `[ ]` Improve responsive behavior and obvious accessibility issues.

## 5. Authentication

- `[~]` Audit signup, login, logout, persistence, refresh/session recovery.
- `[ ]` Validate password reset and forgot-password flow.
- `[ ]` Validate role-aware redirects and protected routes.
- `[x]` Implement or complete Google login provider boundary.
- `[ ]` Document Google OAuth setup exactly.

## 6. Dashboards

- `[ ]` Audit customer dashboard flows.
- `[ ]` Audit professional dashboard flows.
- `[ ]` Ensure professional onboarding supports categories/subcategories/services.
- `[ ]` Audit admin dashboard functionality and permissions.
- `[ ]` Remove or fix dead dashboard links/actions.

## 7. Integrations

- `[ ]` Audit Stripe payments.
- `[ ]` Audit Stripe Connect onboarding and status handling.
- `[ ]` Audit Google Maps/Places/geocoding setup.
- `[ ]` Audit Cloudinary media handling.
- `[~]` Audit Firebase notifications.
- `[ ]` Audit email configuration and templates.
- `[~]` Audit Twilio/communications if present.
- `[~]` Audit Persona/Certn verification if present.
- `[ ]` Mark each integration as verified locally or credential-dependent.

## 8. Security

- `[ ]` Check DEBUG, ALLOWED_HOSTS, CORS, CSRF, HTTPS/proxy settings.
- `[~]` Check auth token/session handling.
- `[ ]` Check password reset safety.
- `[ ]` Check webhook signature verification.
- `[ ]` Check upload validation.
- `[ ]` Check IDOR, mass assignment, and privilege escalation risks.
- `[x]` Check sensitive data exposure in API responses and frontend pages.

## 9. Testing And Verification

- `[x]` Run backend dependency/install sanity check if needed.
- `[x]` Run `python backend\manage.py check`.
- `[x]` Run `python backend\manage.py makemigrations --check`.
- `[x]` Run `python backend\manage.py migrate`.
- `[x]` Run backend tests.
- `[x]` Run frontend dependency/install sanity check if needed.
- `[x]` Run frontend lint.
- `[x]` Run frontend typecheck if configured.
- `[x]` Run frontend production build.
- `[ ]` Start backend locally.
- `[ ]` Start frontend locally.
- `[ ]` Browser-test major customer/professional/auth/navigation flows.

## 10. Documentation And Deployment

- `[ ]` Update `README.md` as needed.
- `[ ]` Add or update `SETUP.md` / `DEPLOYMENT.md` if needed.
- `[ ]` Finalize sanitized backend env example.
- `[ ]` Finalize sanitized frontend env example.
- `[ ]` Document exact credential setup for every real external provider.
- `[ ]` Document Hostinger Ubuntu VPS deployment steps.
- `[ ]` Document admin setup and initial platform configuration.

## 11. Final Report Inputs

- `[ ]` Production readiness status.
- `[ ]` What changed by area.
- `[ ]` Actual command results.
- `[ ]` Credential-dependent items only.
- `[ ]` Complete env file content.
- `[ ]` Local run instructions.
- `[ ]` Manual test guide.
- `[ ]` Production build commands.
- `[ ]` Deployment guide.
- `[ ]` Admin setup guide.
- `[ ]` External dashboard configuration.
- `[ ]` Final verification checklist.
