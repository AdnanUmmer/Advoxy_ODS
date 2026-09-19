import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import { getProfessional, getReviews } from "@/lib/api";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const professional = await getProfessional(Number(id));
    return {
      title: `${professional.display_name} | Advoxy`,
      description: `View ${professional.display_name}'s verified services and availability on Advoxy.`,
    };
  } catch {
    return { title: "Professional | Advoxy" };
  }
}

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue) {
  return Array.isArray(value) ? value[0] : value;
}

function buildBookingHref(serviceId: number | undefined, context: Record<string, SearchValue>) {
  if (!serviceId) return "/search";
  const params = new URLSearchParams({ professionalService: String(serviceId) });
  ["service", "service_name", "location", "when", "booking_type", "date", "time", "latitude", "longitude"].forEach((key) => {
    const value = firstValue(context[key]);
    if (value) params.set(key, value);
  });
  return `/book?${params.toString()}`;
}

function buildSearchHref(context: Record<string, SearchValue>) {
  const params = new URLSearchParams();
  Object.entries(context).forEach(([key, value]) => {
    const actual = firstValue(value);
    if (actual) params.set(key, actual);
  });
  return `/search${params.size ? `?${params.toString()}` : ""}`;
}

export default async function ProfessionalPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const { id } = await params;
  const context = await searchParams;
  let professional;
  try {
    professional = await getProfessional(Number(id));
  } catch {
    notFound();
  }
  if (!professional) notFound();

  const reviews = await getReviews(professional.id).catch(() => []);
  const requestedCatalogService = firstValue(context.service);
  const selectedService =
    professional.services.find((service) => requestedCatalogService && String(service.service_catalog_id) === requestedCatalogService) ??
    professional.services[0];
  const lowestPrice = professional.services.length
    ? Math.min(...professional.services.map((service) => Number.parseFloat(service.price)))
    : null;
  const initials = professional.display_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <>
      <SiteHeader />

      <main className="professional-page">
        <div className="breadcrumb">
          <Link href="/search">Professionals</Link> / {professional.display_name}
        </div>

        <section className="professional-hero">
          <div className="professional-avatar">{initials || "AP"}</div>
          <div>
            <p className="eyebrow">
              <span>{professional.is_online ? "Online now" : "Scheduled booking"}</span>
              Verified professional
            </p>
            <h1>{professional.display_name}</h1>
            <div className="professional-role">
              {professional.services[0]?.name ?? "Beauty professional"} · {professional.area || "Calgary"}
            </div>
            <div className="professional-rating">
              <span className="rating">★ {professional.average_rating ?? "New"}</span>
              <span>{professional.review_count} reviews</span>
              <span>{professional.years_experience} years experience</span>
              {professional.distance_km !== null && <span>{professional.distance_km.toFixed(1)} km away</span>}
            </div>
            <div className="professional-actions">
              <Link
                className="btn btn-primary"
                href={buildBookingHref(selectedService?.id, context)}
              >
                Continue to book
              </Link>
              <Link className="btn btn-outline" href={buildSearchHref(context)}>
                Back to results
              </Link>
            </div>
            <div className="verification-note">
              <strong>Privacy-safe profile</strong>
              <span>Only public service, rating, and profile details are shown. Personal contact and identity-check details stay private.</span>
            </div>
          </div>
        </section>

        <section className="professional-grid">
          <div>
            <div className="professional-about">
              <h2>About</h2>
              <p>
                {professional.bio || "An independent Advoxy professional focused on thoughtful, at-home beauty services."}
              </p>
            </div>

            <div className="profile-section" id="services">
              <h2>Services</h2>
              {professional.services.length === 0 ? (
                <div className="empty-state">No services are available from this professional right now.</div>
              ) : (
                professional.services.map((service) => (
                  <Link className="professional-service" href={buildBookingHref(service.id, context)} key={service.id}>
                    <div>
                      <h3>{service.name}</h3>
                      <p>{service.category} · {service.subcategory} · {service.duration_minutes} min</p>
                    </div>
                    <strong>
                      ${Number.parseFloat(service.price).toFixed(0)} <small>CAD</small>
                    </strong>
                  </Link>
                ))
              )}
            </div>
          </div>

          <aside className="profile-booking-panel">
            <p className="eyebrow">Booking</p>
            <div className="price-lead">
              From ${lowestPrice ? Math.round(lowestPrice) : "75"} <small>CAD</small>
            </div>
            <div className="rating-line">
              ★ {professional.average_rating ?? "New"} · {professional.review_count} reviews
            </div>

            <label className="field">
              <span>Service</span>
              <select defaultValue={selectedService?.id ?? ""}>
                {professional.services.length === 0 ? (
                  <option value="">No services available</option>
                ) : (
                  professional.services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} · ${Number.parseFloat(service.price).toFixed(0)}
                    </option>
                  ))
                )}
              </select>
            </label>

            <Link
              className="btn btn-primary"
              href={buildBookingHref(selectedService?.id, context)}
            >
              Book this professional
            </Link>
            <div className="booking-note">You will review the appointment details before payment authorization.</div>

            <div className="profile-side-section" id="portfolio">
              <h2>Portfolio</h2>
              <div className="empty-state">Portfolio images will appear here when this professional adds them.</div>
            </div>

            <div className="profile-side-section" id="reviews">
              <h2>Reviews</h2>
              <div className="review-summary">
                <div className="big">{professional.average_rating ?? "New"}</div>
                <div>
                  <div className="stars">★★★★★</div>
                  <div className="count">{professional.review_count} reviews · {professional.years_experience} years on Advoxy</div>
                </div>
              </div>
              <div className="reviews-list">
                {reviews.length === 0 ? (
                  <div className="empty-state">Reviews from completed bookings will appear here.</div>
                ) : (
                  reviews.map((review) => (
                    <div key={review.id} className="review-card">
                      <div className="review-header">
                        <span className="review-user">{review.customer_name}</span>
                        <span className="review-rating">★ {review.rating}</span>
                      </div>
                      <p className="review-body">{review.comment}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </section>
      </main>
    </>
  );
}
