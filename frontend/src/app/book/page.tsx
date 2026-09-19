"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  CardNumberElement,
  CardExpiryElement,
  CardCvcElement,
  Elements,
  useElements,
  useStripe,
} from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import SiteHeader from "@/components/SiteHeader";
import DateTimePicker from "@/components/DateTimePicker";
import {
  ApiError,
  Address,
  cancelBooking,
  confirmPaymentIntent,
  createAddress,
  createBooking,
  createPaymentIntent,
  getAvailability,
  getBooking,
  getAddresses,
  getProfessionalServices,
  autocompleteLocation,
  getPlaceDetails,
  geocodeAddress,
  reverseGeocode,
  ProfessionalService,
  AvailabilitySlot,
} from "@/lib/api";

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

function money(value: string) {
  return `$${Number.parseFloat(value).toFixed(0)} CAD`;
}

function readableStatus(status: string) {
  return status.toLowerCase().replaceAll("_", " ");
}

function BookingDetail({ booking }: { booking: import("@/lib/api").Booking }) {
  const date = booking.scheduled_time
    ? new Date(booking.scheduled_time).toLocaleString([], {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "Immediate request";
  const time = booking.scheduled_time
    ? new Date(booking.scheduled_time).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      })
    : "Match in progress";

  return (
    <>
      <SiteHeader />
      <main className="booking-detail-page">
        <div className="booking-detail-topline">
          <Link className="step-back" href="/dashboard">← My bookings</Link>
          <span className={`detail-status status-${booking.status.toLowerCase()}`}>{readableStatus(booking.status)}</span>
        </div>
        <section className="booking-detail-hero">
          <div>
            <p className="eyebrow"><span>Booking #{booking.id}</span> {booking.booking_type === "INSTANT" ? "Instant visit" : "Scheduled visit"}</p>
            <h1>{booking.service_name || "Your appointment"} <em>details.</em></h1>
            <p className="lead">Everything for this appointment, in one place.</p>
          </div>
          <div className="detail-professional-badge"><span>{(booking.professional_name || "Advoxy").split(" ").map((part) => part[0]).join("").slice(0, 2)}</span><div><small>Professional</small><strong>{booking.professional_name || "Finding a professional"}</strong></div></div>
        </section>
        <div className="booking-detail-grid">
          <section className="detail-panel"><p className="eyebrow">Appointment</p><div className="detail-list"><div><span>Service</span><strong>{booking.service_name || "Beauty service"}</strong></div><div><span>Category</span><strong>{booking.service_category || "Hair & beauty"}</strong></div><div><span>Date</span><strong>{date}</strong></div><div><span>Time</span><strong>{time}</strong></div><div><span>Duration</span><strong>{booking.duration_minutes} minutes</strong></div></div></section>
          <section className="detail-panel"><p className="eyebrow">Location & payment</p><div className="detail-list"><div><span>Service address</span><strong>{booking.address_label || "Saved address"}</strong><small>{booking.address_full || "Address details unavailable"}</small></div><div><span>Payment status</span><strong>{booking.status === "CONFIRMED_COMPLETE" ? "Captured" : "Authorized after checkout"}</strong></div><div><span>Total</span><strong>{money(booking.total_amount)}</strong></div></div><Link className="btn btn-primary detail-chat-link" href="/dashboard">Open booking chat</Link></section>
        </div>
        <section className="detail-next"><strong>What happens next?</strong><span>Your professional will keep the appointment status updated. Payment is captured only after confirmed completion.</span></section>
      </main>
    </>
  );
}

function PaymentForm({
  clientSecret,
  onSuccess,
  onError,
}: {
  clientSecret: string;
  onSuccess: () => void;
  onError: (message: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setSubmitting(true);
    const cardNumber = elements.getElement(CardNumberElement);
    const cardExpiry = elements.getElement(CardExpiryElement);
    const cardCvc = elements.getElement(CardCvcElement);
    if (!cardNumber || !cardExpiry || !cardCvc) {
      onError("Payment form is unavailable. Refresh and try again.");
      setSubmitting(false);
      return;
    }
    const postalCode = String(
      new FormData(event.currentTarget).get("postal_code") ?? "",
    ).trim();
    const result = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: cardNumber,
        billing_details: { address: { postal_code: postalCode || undefined } },
      },
    });
    if (result.error)
      onError(result.error.message ?? "Stripe could not confirm this payment.");
    else if (
      result.paymentIntent?.status === "requires_capture" ||
      result.paymentIntent?.status === "succeeded"
    )
      onSuccess();
    else
      onError(
        `Payment requires another step: ${result.paymentIntent?.status ?? "unknown"}.`,
      );
    setSubmitting(false);
  }

  const elementOptions = {
    style: {
      base: {
        color: "#211f1c",
        fontFamily: "inherit",
        fontSize: "15px",
        "::placeholder": { color: "#8b877d" },
      },
    },
  };
  return (
    <form className="payment-form" onSubmit={submit}>
      <label className="stripe-field">
        <span>Card number</span>
        <div>
          <CardNumberElement options={elementOptions} />
        </div>
      </label>
      <div className="stripe-field-row">
        <label className="stripe-field">
          <span>Expiry date</span>
          <div>
            <CardExpiryElement options={elementOptions} />
          </div>
        </label>
        <label className="stripe-field">
          <span>Security code</span>
          <div>
            <CardCvcElement options={elementOptions} />
          </div>
        </label>
      </div>
      <label className="stripe-field">
        <span>Postal code</span>
        <div>
          <input
            name="postal_code"
            autoComplete="postal-code"
            placeholder="A1A 1A1"
          />
        </div>
      </label>
      <p className="payment-test-note">
        Test mode: use <strong>4242 4242 4242 4242</strong>, any future expiry,
        any 3-digit CVC.
      </p>
      <button
        className="submit-btn"
        type="submit"
        disabled={!stripe || submitting}
      >
        {submitting ? "Confirming payment..." : "Authorize payment securely"}
      </button>
    </form>
  );
}

export default function BookPage() {
  const router = useRouter();
  const [services, setServices] = useState<ProfessionalService[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [serviceId, setServiceId] = useState(() =>
    typeof window === "undefined"
      ? ""
      : (new URLSearchParams(window.location.search).get(
          "professionalService",
        ) ?? ""),
  );
  const [categorySlug, setCategorySlug] = useState("");
  const [audience, setAudience] = useState("");
  const [subcategorySlug, setSubcategorySlug] = useState("");
  const [addressId, setAddressId] = useState("");
  const [bookingType, setBookingType] = useState<"INSTANT" | "SCHEDULED">(
    "INSTANT",
  );
  const [bookingStep, setBookingStep] = useState(1);
  const [serviceChoice, setServiceChoice] = useState("");
  const [scheduledTime, setScheduledTime] = useState("");
  const [slots, setSlots] = useState<AvailabilitySlot[]>([]);
  const [slotId, setSlotId] = useState("");
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState<
    { place_id: string; description: string }[]
  >([]);
  const [locationState, setLocationState] = useState<
    "idle" | "searching" | "detecting" | "ready" | "error"
  >("idle");
  const [locationMessage, setLocationMessage] = useState("");
  const [newAddress, setNewAddress] = useState({
    label: "Home",
    full_address: "",
    latitude: "51.0447",
    longitude: "-114.0719",
  });
  const [status, setStatus] = useState<
    "loading" | "ready" | "error" | "submitting" | "success"
  >("loading");
  const [message, setMessage] = useState("");
  const [paymentSecret, setPaymentSecret] = useState("");
  const [createdBookingId, setCreatedBookingId] = useState<number | null>(null);
  const [paymentComplete, setPaymentComplete] = useState(false);
  const [bookingDetail, setBookingDetail] = useState<import("@/lib/api").Booking | null>(null);

  useEffect(() => {
    const query = newAddress.full_address.trim();
    if (!showAddressForm || query.length < 3) {
      return;
    }
    const timer = window.setTimeout(() => {
      setLocationState("searching");
      autocompleteLocation(query)
        .then((result) => {
          setAddressSuggestions(result.predictions);
          setLocationState("idle");
        })
        .catch(() => {
          setAddressSuggestions([]);
          setLocationState("error");
          setLocationMessage(
            "Address search is unavailable. Use the location button or try again.",
          );
        });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [newAddress.full_address, showAddressForm]);

  useEffect(() => {
    if (!localStorage.getItem("advoxy_token")) {
      router.push(
        `/signup?next=${encodeURIComponent(`${window.location.pathname}${window.location.search}`)}`,
      );
      return;
    }

    Promise.all([getProfessionalServices(), getAddresses()])
      .then(([nextServices, nextAddresses]) => {
        const currentParams = new URLSearchParams(window.location.search);
        const requestedBookingId = currentParams.get("bookingId");
        if (requestedBookingId) {
          void getBooking(Number(requestedBookingId)).then((booking) => {
            setBookingDetail(booking);
            setStatus("ready");
          }).catch(() => {
            setStatus("error");
            setMessage("We could not load this booking. Return to your bookings and try again.");
          });
          return;
        }
        setServices(nextServices);
        setAddresses(nextAddresses);
        const requestedServiceId = currentParams.get("professionalService");
        const initialService =
          nextServices.find(
            (service) => String(service.id) === requestedServiceId,
          ) ?? nextServices[0];
        setServiceId(String(initialService?.id ?? ""));
        setServiceChoice(initialService?.service_slug ?? "");
        setCategorySlug(initialService?.category_slug ?? "");
        setAudience(
          initialService?.category_slug === "hair" ||
            initialService?.category_slug === "nails"
            ? initialService.audience === "MEN" ||
              initialService.audience === "WOMEN" ||
              initialService.audience === "KIDS"
              ? initialService.audience
              : "WOMEN"
            : "",
        );
        setSubcategorySlug(initialService?.subcategory_slug ?? "");
        const requestedBookingType = currentParams.get("booking_type");
        setBookingType(
          requestedBookingType === "SCHEDULED" ? "SCHEDULED" : "INSTANT",
        );
        const date = currentParams.get("date");
        const time = currentParams.get("time");
        if (date && time) setScheduledTime(`${date}T${time}`);
        setNewAddress((current) => ({
          ...current,
          full_address: currentParams.get("location") || current.full_address,
          latitude: currentParams.get("latitude") || current.latitude,
          longitude: currentParams.get("longitude") || current.longitude,
        }));
        setAddressId(
          String(
            nextAddresses.find((address) => address.is_default)?.id ??
              nextAddresses[0]?.id ??
              "",
          ),
        );
        setStatus("ready");
        void getAvailability()
          .then((nextSlots) => {
            setSlots(nextSlots);
            const requestedTime = date && time ? new Date(`${date}T${time}`).getTime() : 0;
            const matchingSlot = nextSlots.find((slot) => Math.abs(new Date(slot.start_time).getTime() - requestedTime) < 60000);
            if (matchingSlot) setSlotId(String(matchingSlot.id));
          })
          .catch(() => setSlots([]));
      })
      .catch(() => {
        setStatus("error");
        setMessage(
          "We could not load booking options. Make sure the Django API is running and seeded.",
        );
      });
  }, [router]);

  async function handleAddressSubmit() {
    if (!newAddress.full_address.trim()) {
      setLocationMessage("Enter a complete service address first.");
      return;
    }
    setLocationState("searching");
    try {
      let addressToSave = newAddress;
      if (!addressToSave.latitude || !addressToSave.longitude) {
        const geocoded = await geocodeAddress(addressToSave.full_address);
        addressToSave = {
          ...addressToSave,
          full_address: geocoded.formatted_address,
          latitude: String(geocoded.latitude),
          longitude: String(geocoded.longitude),
        };
        setNewAddress(addressToSave);
      }
      const address = await createAddress({
        ...addressToSave,
        is_default: addresses.length === 0,
      });
      setAddresses((current) => [...current, address]);
      setAddressId(String(address.id));
      setShowAddressForm(false);
      setAddressSuggestions([]);
      setLocationState("ready");
      setLocationMessage("Address saved.");
    } catch {
      setLocationState("error");
      setLocationMessage(
        "We could not verify that address. Try a fuller address or use your current location.",
      );
    }
  }

  async function selectAddressSuggestion(placeId: string) {
    setLocationState("searching");
    try {
      const place = await getPlaceDetails(placeId);
      setNewAddress((current) => ({
        ...current,
        full_address: place.formatted_address,
        latitude: String(place.latitude),
        longitude: String(place.longitude),
      }));
      setAddressSuggestions([]);
      setLocationState("ready");
      setLocationMessage("Address confirmed.");
    } catch {
      setLocationState("error");
      setLocationMessage(
        "We could not confirm that address. Choose another suggestion.",
      );
    }
  }

  function detectLocation() {
    if (!navigator.geolocation) {
      setLocationState("error");
      setLocationMessage(
        "Location detection is not supported by this browser. Search for your address instead.",
      );
      return;
    }
    setLocationState("detecting");
    setLocationMessage("");
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const result = await reverseGeocode(
            coords.latitude,
            coords.longitude,
          );
          setNewAddress((current) => ({
            ...current,
            full_address: result.formatted_address,
            latitude: String(coords.latitude),
            longitude: String(coords.longitude),
          }));
          setLocationState("ready");
          setLocationMessage("Current location detected.");
        } catch {
          setLocationState("error");
          setLocationMessage(
            "We could not identify your location. Search for your address instead.",
          );
        }
      },
      () => {
        setLocationState("error");
        setLocationMessage(
          "Location permission was not granted. Search for your address instead.",
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  }

  async function handleBookingSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!serviceId || !addressId) {
      setMessage("Choose a service and add a service address first.");
      return;
    }
    if (bookingType === "INSTANT" && !selectedService?.is_available_now) {
      setMessage(
        "Instant booking is not available for this professional. Choose a scheduled time instead.",
      );
      return;
    }
    setStatus("submitting");
    setMessage("");
    let pendingBookingId: number | null = null;
    try {
      const booking = await createBooking({
        professional_service: Number(serviceId),
        address: Number(addressId),
        booking_type: bookingType,
        ...(bookingType === "SCHEDULED" && scheduledTime && slotId
          ? {
              scheduled_time: new Date(scheduledTime).toISOString(),
              availability_slot: Number(slotId),
            }
          : {}),
      });
      pendingBookingId = booking.id;
      setCreatedBookingId(booking.id);
      if (!stripePromise) {
        setStatus("ready");
        setMessage(
          "Stripe is not configured for this environment. The booking was not left active.",
        );
        await cancelBooking(booking.id);
        return;
      }
      const payment = await createPaymentIntent(booking.id);
      setPaymentSecret(payment.client_secret);
      setStatus("success");
      setMessage(
        `Booking #${booking.id} is ready for secure payment authorization.`,
      );
    } catch (error) {
      if (pendingBookingId) {
        await cancelBooking(pendingBookingId).catch(() => undefined);
      }
      setStatus("ready");
      setMessage(
        error instanceof ApiError
          ? "That booking could not be created. Please review the required fields."
          : "The API is unavailable right now.",
      );
    }
  }

  if (status === "error") {
    return (
      <main className="centered-state">
        <p className="eyebrow">Booking setup</p>
        <h1>{message}</h1>
        <Link className="btn btn-primary" href="/signup">
          Create customer account
        </Link>
      </main>
    );
  }

  if (bookingDetail) return <BookingDetail booking={bookingDetail} />;

  const selectedService = services.find(
    (service) => String(service.id) === serviceId,
  );
  const categoryOptions = Array.from(
    new Map(
      services.map((service) => [service.category_slug, service.category_name]),
    ).entries(),
  );
  const audienceOptions =
    categorySlug === "hair" || categorySlug === "nails"
      ? ["MEN", "WOMEN", "KIDS"]
      : [];
  const matchesAudience = (service: ProfessionalService) =>
    !audience ||
    service.audience === audience ||
    (categorySlug === "nails" && service.audience === "UNISEX");
  const groupOptions = Array.from(
    new Map(
      services
        .filter(
          (service) =>
            service.category_slug === categorySlug && matchesAudience(service),
        )
        .map((service) => [service.subcategory_slug, service.subcategory_name]),
    ).entries(),
  );
  const selectableServices = services.filter(
    (service) =>
      service.category_slug === categorySlug &&
      matchesAudience(service) &&
      (!subcategorySlug || service.subcategory_slug === subcategorySlug),
  );
  const serviceChoices = Array.from(
    new Map(
      selectableServices.map((service) => [
        service.service_slug,
        service.service_name,
      ]),
    ).entries(),
  );
  const professionalChoices = selectableServices.filter(
    (service) => !serviceChoice || service.service_slug === serviceChoice,
  );
  const bookableSlots = slots.filter(
    (slot) =>
      !slot.is_booked &&
      (!selectedService || slot.professional === selectedService.professional),
  );
  function chooseCategory(nextCategory: string) {
    setCategorySlug(nextCategory);
    setAudience("");
    setSubcategorySlug("");
    setServiceId("");
    setServiceChoice("");
    setBookingStep(2);
  }

  function chooseAudience(nextAudience: string) {
    const nextServices = services.filter(
      (service) =>
        service.category_slug === categorySlug &&
        (service.audience === nextAudience ||
          (categorySlug === "nails" && service.audience === "UNISEX")),
    );
    const nextGroup = nextServices[0]?.subcategory_slug ?? "";
    setAudience(nextAudience);
    setSubcategorySlug(nextGroup);
    setServiceId(String(nextServices[0]?.id ?? ""));
    setServiceChoice("");
    setBookingStep(3);
  }

  function chooseGroup(nextGroup: string) {
    setSubcategorySlug(nextGroup);
    setServiceId("");
    setServiceChoice("");
    setBookingStep(4);
  }

  function chooseService(nextServiceSlug: string) {
    setServiceChoice(nextServiceSlug);
    setServiceId("");
    setBookingStep(5);
  }

  function chooseProfessional(nextProfessionalServiceId: string) {
    const professionalService = professionalChoices.find(
      (service) => String(service.id) === nextProfessionalServiceId,
    );
    setServiceId(nextProfessionalServiceId);
    if (professionalService && !professionalService.is_available_now) {
      setBookingType("SCHEDULED");
    }
    setBookingStep(6);
  }

  function openSchedulePicker() {
    setBookingType("SCHEDULED");
  }

  if (paymentComplete && createdBookingId) {
    return (
      <>
        <SiteHeader />
        <main className="centered-state payment-success">
          <p className="eyebrow">Payment authorized</p>
          <h1>
            Your booking is <em>secured.</em>
          </h1>
          <p className="lead">
            Booking #{createdBookingId} is confirmed. Your card will only be
            captured after the appointment is completed.
          </p>
          <div className="success-actions">
            <Link className="btn btn-primary" href="/dashboard">
              View my bookings
            </Link>
            <Link className="btn btn-outline" href="/">
              Continue exploring
            </Link>
          </div>
        </main>
      </>
    );
  }

  if (paymentSecret && createdBookingId && stripePromise) {
    return (
      <>
        <SiteHeader />
        <main className="booking-layout">
          <section className="booking-intro">
            <p className="eyebrow">
              <span>02 / 02</span> Secure checkout
            </p>
            <h1>
              One last step, then it&apos;s <em>yours.</em>
            </h1>
            <p className="lead">
              Your payment is authorized securely by Stripe and captured only
              after confirmed completion.
            </p>
          </section>
          <section className="booking-panel">
            <h2 className="auth-form-title">
              Authorize booking #{createdBookingId}
            </h2>
            <Elements
              stripe={stripePromise}
              options={{ clientSecret: paymentSecret }}
            >
              <PaymentForm
                clientSecret={paymentSecret}
                onSuccess={async () => {
                  try {
                    await confirmPaymentIntent(
                      paymentSecret.split("_secret")[0],
                    );
                    setPaymentSecret("");
                    setPaymentComplete(true);
                  } catch {
                    setMessage(
                      "Stripe confirmed the card, but Advoxy could not verify the payment. Please refresh before trying again.",
                    );
                  }
                }}
                onError={setMessage}
              />
            </Elements>
            {message && <p className="form-message error">{message}</p>}
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <SiteHeader />
      <main className="booking-layout">
        <section className="booking-intro">
          <p className="eyebrow">
            <span>01 / 02</span> Your appointment
          </p>
          <h1>
            Make the next hour feel <em>well spent.</em>
          </h1>
          <p className="lead">
            Choose a service, tell us where to meet you, and we will keep every
            handoff visible.
          </p>
          <div className="booking-note">
            <strong>Secure by design</strong>
            <span>
              Your card is pre-authorized and only captured after confirmed
              completion.
            </span>
          </div>
        </section>

        <section className="booking-panel" aria-label="Create booking">
          <form onSubmit={handleBookingSubmit}>
            <div className="booking-progress">
              <span className="active">1</span>
              <i />
              <span className={bookingStep >= 2 ? "active" : ""}>2</span>
              <i />
              <span className={bookingStep >= 4 ? "active" : ""}>3</span>
              <i />
              <span className={bookingStep >= 6 ? "active" : ""}>4</span>
            </div>
            <p className="booking-step-label">
              Step{" "}
              {bookingStep <= 1
                ? 1
                : bookingStep <= 3
                  ? 2
                  : bookingStep <= 5
                    ? 3
                    : 4}{" "}
              of 4
            </p>

            {bookingStep === 1 && (
              <div className="booking-step">
                <h2>What would you like to book?</h2>
                <p>Start with a service category.</p>
                <div className="option-cards">
                  {categoryOptions.map(([slug, name]) => (
                    <button
                      className={`option-card ${categorySlug === slug ? "selected" : ""}`}
                      type="button"
                      key={slug}
                      onClick={() => chooseCategory(slug)}
                    >
                      <strong>{name}</strong>
                      <span>
                        {slug === "hair"
                          ? "Cuts, colour and styling"
                          : "Manicure, pedicure and nail art"}
                      </span>
                      <b>→</b>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {bookingStep === 2 && (
              <div className="booking-step">
                <button
                  className="step-back"
                  type="button"
                  onClick={() => setBookingStep(1)}
                >
                  ← Category
                </button>
                <h2>Who is this service for?</h2>
                <p>Choose the experience that fits you.</p>
                <div className="option-cards compact">
                  {audienceOptions.map((value) => (
                    <button
                      className={`option-card ${audience === value ? "selected" : ""}`}
                      type="button"
                      key={value}
                      onClick={() => chooseAudience(value)}
                    >
                      <strong>{value[0] + value.slice(1).toLowerCase()}</strong>
                      <span>Explore {value.toLowerCase()} services</span>
                      <b>→</b>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {bookingStep === 3 && (
              <div className="booking-step">
                <button
                  className="step-back"
                  type="button"
                  onClick={() => setBookingStep(2)}
                >
                  ← Audience
                </button>
                <h2>Choose a service group</h2>
                <p>Find the kind of appointment you have in mind.</p>
                <div className="option-cards compact">
                  {groupOptions.map(([slug, name]) => (
                    <button
                      className={`option-card ${subcategorySlug === slug ? "selected" : ""}`}
                      type="button"
                      key={slug}
                      onClick={() => chooseGroup(slug)}
                    >
                      <strong>{name}</strong>
                      <span>View available services</span>
                      <b>→</b>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {bookingStep === 4 && (
              <div className="booking-step">
                <button
                  className="step-back"
                  type="button"
                  onClick={() =>
                    setBookingStep(categorySlug === "hair" ? 2 : 1)
                  }
                >
                  ← Service group
                </button>
                <h2>Choose your service</h2>
                <p>Select the service you would like to book.</p>
                <div className="service-choice-list">
                  {serviceChoices.map(([slug, name]) => (
                    <button
                      className="service-choice"
                      type="button"
                      key={slug}
                      onClick={() => chooseService(slug)}
                    >
                      <span>
                        <strong>{name}</strong>
                        <small>
                          {
                            selectableServices.filter(
                              (service) => service.service_slug === slug,
                            ).length
                          }{" "}
                          professionals available
                        </small>
                      </span>
                      <b>→</b>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {bookingStep === 5 && (
              <div className="booking-step">
                <button
                  className="step-back"
                  type="button"
                  onClick={() => setBookingStep(4)}
                >
                  ← Services
                </button>
                <h2>Choose your professional</h2>
                <p>
                  Compare professionals offering{" "}
                  {serviceChoices.find(
                    ([slug]) => slug === serviceChoice,
                  )?.[1] ?? "this service"}
                  .
                </p>
                <div className="professional-choice-list">
                  {professionalChoices.map((service) => (
                    <button
                      className="professional-choice"
                      type="button"
                      key={service.id}
                      onClick={() => chooseProfessional(String(service.id))}
                    >
                      <span className="choice-avatar">
                        {service.professional_name
                          .split(" ")
                          .map((part) => part[0])
                          .join("")
                          .slice(0, 2)}
                      </span>
                      <span>
                        <strong>{service.professional_name}</strong>
                        <small>
                          {service.professional_rating
                            ? `★ ${service.professional_rating}`
                            : "Verified professional"}{" "}
                          · {money(service.price)}
                        </small>
                      </span>
                      <b>→</b>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {bookingStep >= 6 && (
              <div className="booking-step">
                <button
                  className="step-back"
                  type="button"
                  onClick={() => setBookingStep(5)}
                >
                  ← Professional
                </button>
                {selectedService && (
                  <div className="selection-summary">
                    <strong>{selectedService.service_name}</strong>
                    <span>
                      {selectedService.professional_name} ·{" "}
                      {selectedService.duration_minutes} min ·{" "}
                      {money(selectedService.price)}
                    </span>
                  </div>
                )}
                <div className="choice-label">How would you like to book?</div>
                <div className="choice-grid">
                  <button
                    type="button"
                    disabled={!selectedService?.is_available_now}
                    className={`${bookingType === "INSTANT" ? "choice active" : "choice"} ${!selectedService?.is_available_now ? "choice disabled" : ""}`}
                    onClick={() => setBookingType("INSTANT")}
                  >
                    <strong>Instant</strong>
                    <span>
                      {selectedService?.is_available_now
                        ? "Match me now · +$15 priority"
                        : "Not available right now"}
                    </span>
                  </button>
                  <button
                    type="button"
                    className={
                      bookingType === "SCHEDULED" ? "choice active" : "choice"
                    }
                    onClick={openSchedulePicker}
                  >
                    <strong>Schedule</strong>
                    <span>
                      {selectedService?.is_available_now
                        ? "Choose an open time"
                        : "Choose from available times"}
                    </span>
                  </button>
                </div>
              </div>
            )}

            {false && (
              <label className="field">
                <span>Category</span>
                <select
                  value={categorySlug}
                  onChange={(event) => chooseCategory(event.target.value)}
                  required
                  disabled={status === "loading"}
                >
                  <option value="">Choose Hair or Nails</option>
                  {categoryOptions.map(([slug, name]) => (
                    <option key={slug} value={slug}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {false && (
              <div>
                {categorySlug === "hair" && (
                  <label className="field">
                    <span>Audience</span>
                    <select
                      value={audience}
                      onChange={(event) => chooseAudience(event.target.value)}
                      required
                    >
                      <option value="">Choose an audience</option>
                      {audienceOptions.map((value) => (
                        <option key={value} value={value}>
                          {value[0] + value.slice(1).toLowerCase()}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <label className="field">
                  <span>
                    {categorySlug === "hair" ? "Hair service" : "Nail service"}
                  </span>
                  <select
                    value={subcategorySlug}
                    onChange={(event) => chooseGroup(event.target.value)}
                    required
                    disabled={!categorySlug}
                  >
                    <option value="">Choose a service group</option>
                    {groupOptions.map(([slug, name]) => (
                      <option key={slug} value={slug}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Service and professional</span>
                  <select
                    value={serviceId}
                    onChange={(event) => setServiceId(event.target.value)}
                    required
                    disabled={!subcategorySlug || status === "loading"}
                  >
                    <option value="">Select a service</option>
                    {selectableServices.map((service) => (
                      <option key={service.id} value={service.id}>
                        {service.service_name} · {service.professional_name} ·{" "}
                        {money(service.price)}
                      </option>
                    ))}
                  </select>
                </label>

                {selectedService && (
                  <div className="selection-summary">
                    <strong>{selectedService?.service_name ?? ""}</strong>
                    <span>
                      {selectedService?.professional_name ?? ""} ·{" "}
                      {selectedService?.duration_minutes ?? 0} min ·{" "}
                      {money(selectedService?.price ?? "0")}
                    </span>
                  </div>
                )}

                <div className="choice-label">When would you like it?</div>
                <div className="choice-grid">
                  <button
                    type="button"
                    className={
                      bookingType === "INSTANT" ? "choice active" : "choice"
                    }
                    onClick={() => setBookingType("INSTANT")}
                  >
                    <strong>Instant</strong>
                    <span>Match me now · +$15 priority</span>
                  </button>
                  <button
                    type="button"
                    className={
                      bookingType === "SCHEDULED" ? "choice active" : "choice"
                    }
                    onClick={openSchedulePicker}
                  >
                    <strong>Schedule</strong>
                    <span>Choose an open time</span>
                  </button>
                </div>
              </div>
            )}

            {bookingStep >= 6 && bookingType === "SCHEDULED" && (
              <DateTimePicker
                value={scheduledTime}
                slots={bookableSlots}
                onChange={(value, nextSlotId) => {
                  setScheduledTime(value);
                  setSlotId(nextSlotId ?? "");
                }}
              />
            )}

            {bookingStep >= 6 && (
              <>
                <label className="field">
                  <span>Service address</span>
                  <select
                    value={addressId}
                    onChange={(event) => setAddressId(event.target.value)}
                    required
                  >
                    <option value="">Choose an address</option>
                    {addresses.map((address) => (
                      <option key={address.id} value={address.id}>
                        {address.label || "Saved address"} ·{" "}
                        {address.full_address}
                      </option>
                    ))}
                  </select>
                </label>

                {!showAddressForm ? (
                  <button
                    className="text-action"
                    type="button"
                    onClick={() => setShowAddressForm(true)}
                  >
                    + Add a new address
                  </button>
                ) : (
                  <div className="address-form">
                    <div className="address-form-head">
                      <div>
                        <strong>Where should we meet?</strong>
                        <span>Use your location or search for an address.</span>
                      </div>
                      <button
                        className="text-action"
                        type="button"
                        onClick={() => {
                          setShowAddressForm(false);
                          setAddressSuggestions([]);
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                    <label className="field">
                      <span>Address label</span>
                      <input
                        value={newAddress.label}
                        onChange={(event) =>
                          setNewAddress({
                            ...newAddress,
                            label: event.target.value,
                          })
                        }
                        placeholder="Home, office, hotel"
                      />
                    </label>
                    <div className="location-search">
                      <label className="field">
                        <span>Search address</span>
                        <input
                          value={newAddress.full_address}
                          onChange={(event) => {
                            setNewAddress({
                              ...newAddress,
                              full_address: event.target.value,
                              latitude: "",
                              longitude: "",
                            });
                            setLocationState("idle");
                            setLocationMessage("");
                          }}
                          placeholder="Start typing your address"
                          autoComplete="street-address"
                          required
                        />
                      </label>
                      <button
                        className="btn btn-outline small detect-location"
                        type="button"
                        onClick={detectLocation}
                        disabled={locationState === "detecting"}
                      >
                        {locationState === "detecting"
                          ? "Detecting..."
                          : "Use my location"}
                      </button>
                    </div>
                    {addressSuggestions.length > 0 && (
                      <div
                        className="address-suggestions"
                        role="listbox"
                        aria-label="Address suggestions"
                      >
                        {addressSuggestions.map((suggestion) => (
                          <button
                            type="button"
                            key={suggestion.place_id}
                            onClick={() =>
                              void selectAddressSuggestion(suggestion.place_id)
                            }
                          >
                            {suggestion.description}
                          </button>
                        ))}
                      </div>
                    )}
                    {locationMessage && (
                      <p
                        className={`location-message ${locationState === "error" ? "error" : "success"}`}
                        role="status"
                      >
                        {locationMessage}
                      </p>
                    )}
                    <button
                      className="btn btn-outline small"
                      type="button"
                      onClick={() => void handleAddressSubmit()}
                      disabled={
                        locationState === "searching" ||
                        !newAddress.full_address.trim()
                      }
                    >
                      {locationState === "searching"
                        ? "Verifying address..."
                        : "Save address"}
                    </button>
                  </div>
                )}

                <button
                  className="submit-btn"
                  type="submit"
                  disabled={
                    status === "loading" ||
                    status === "submitting" ||
                    !addresses.length ||
                    (bookingType === "SCHEDULED" && !scheduledTime)
                  }
                >
                  {status === "submitting"
                    ? "Creating booking..."
                    : bookingType === "INSTANT"
                      ? "Request an instant visit"
                      : "Request scheduled visit"}
                </button>
                {message && (
                  <p
                    className={`form-message ${status === "success" ? "success" : "error"}`}
                  >
                    {message}
                  </p>
                )}
              </>
            )}
          </form>
        </section>
      </main>
    </>
  );
}
