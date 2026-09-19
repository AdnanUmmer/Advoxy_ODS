import Link from "next/link";
import { getCategories, getProfessionals, type Category, type Professional } from "@/lib/api";
import SiteHeader from "@/components/SiteHeader";
import HeroSearch from "./HeroSearch";

type UiProfessional = {
  id: number;
  name: string;
  role: string;
  area: string;
  rating: string;
  reviews: string;
  experience: string;
  price: string;
  status: string;
  distance: string;
  nextTime: string;
  gradient: string;
  initials: string;
};

const gradients = [
  "from-[#7a4a6b] to-[#2c1a28]",
  "from-[#4a5a7a] to-[#1a212c]",
  "from-[#5a7a4a] to-[#212c1a]",
  "from-[#7a5a4a] to-[#2c1e1a]",
];

const customerQrPattern = [
  "111111100101111",
  "100000101001001",
  "101110100111101",
  "101110101010101",
  "101110100110101",
  "100000101010001",
  "111111101010111",
  "000000001101000",
  "110111111001101",
  "001001001111010",
  "111101110100111",
  "100010011011001",
  "101110111110101",
  "100000100010001",
  "111111101110111",
];

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function formatPrice(price: string) {
  const amount = Number.parseFloat(price);
  return Number.isFinite(amount) ? `$${Math.round(amount)}` : "$75";
}

function toUiProfessional(professional: Professional, index: number): UiProfessional {
  const primaryService = professional.services[0];
  return {
    id: professional.id,
    name: professional.display_name || "Verified professional",
    role: primaryService?.name ?? "Beauty professional",
    area: professional.area || "Calgary",
    rating: professional.average_rating ?? "New",
    reviews: `${professional.review_count} reviews`,
    experience: `${professional.years_experience} yrs`,
    price: primaryService ? formatPrice(primaryService.price) : "$75",
    status: professional.is_online ? "Online now" : "Scheduled",
    distance: professional.distance_km === null ? "Distance unavailable" : `${professional.distance_km.toFixed(1)} km away`,
    nextTime: professional.is_online ? "Ready now" : "Next scheduled slot",
    gradient: gradients[index % gradients.length],
    initials: initials(professional.display_name || "Advoxy Pro"),
  };
}

async function loadMarketplaceData() {
  try {
    const [apiCategories, apiProfessionals, apiAvailableNow] = await Promise.all([
      getCategories(),
      getProfessionals(),
      getProfessionals({ availableNow: true, bookingType: "INSTANT" }),
    ]);

    return {
      categories: apiCategories
        .filter((category: Category) => category.slug === "hair" || category.slug === "nails")
        .map((category: Category) => ({
          name: category.name,
          slug: category.slug,
          subcategories: category.subcategories,
          className: category.slug === "nails" ? "nails" : "hair",
        })),
      professionals: apiProfessionals.map(toUiProfessional),
      availableNow: apiAvailableNow.slice(0, 3).map(toUiProfessional),
    };
  } catch {
    return {
      categories: [],
      professionals: [],
      availableNow: [],
    };
  }
}

export default async function Home() {
  const { categories, professionals, availableNow } = await loadMarketplaceData();
  return (
    <>
      <SiteHeader />

      <main>
        <section className="wrap hero" id="discover">
          <div>
            <p className="eyebrow">
              <span>01 / 06</span> A better way to book
            </p>
            <h1>
              Your next <em>signature</em> look, closer than you think.
            </h1>
            <p className="lead">
              Find trusted hair and nail professionals in your neighbourhood — selected for their craft, care and availability.
            </p>

            <HeroSearch suggestions={categories.flatMap((category) => category.subcategories.flatMap((subcategory) => subcategory.services.map((service) => ({ id: service.id, name: service.name, category: category.name })) ))} />

            <div className="trust-row" aria-label="Trust features">
              <span>Verified professionals</span>
              <span>Secure pre-authorized payments</span>
              <span>Masked chat and calling</span>
              <span>GPS arrival checks</span>
            </div>
          </div>

          <div className="hero-photo" aria-label="Featured professional">
            <div className="portrait-frame">
              <div className="caption">
                <strong>Kienan M.</strong>
                Barber · Kensington · available today
              </div>
            </div>
            <div className="rating-chip">
              <strong>4.9</strong>
              <span>★★★★★</span>
              <small>avg. rating</small>
            </div>
          </div>
        </section>

        <section className="wrap section" id="services">
          <p className="eyebrow">
            <span>02 / 06</span> Find your ritual
          </p>
          <div className="section-head">
            <h2>
              Start with what <em>feels like you.</em>
            </h2>
            <p>
              From a small refresh to a full transformation, discover the people who make self-care feel effortless.
            </p>
          </div>
          <div className="cat-grid">
            {categories.length === 0 ? <div className="empty-state">No service categories are available yet.</div> : categories.map((category) => (
              <Link className={`cat-card ${category.className}`} href={`/services/${category.slug}`} key={category.name}>
                <h3>{category.name}</h3>
              </Link>
            ))}
          </div>
        </section>

        <section className="wrap section">
          <div className="section-head">
            <div>
              <p className="eyebrow">
                <span>03 / 06</span> A considered shortlist
              </p>
              <h2>
                Curated for <em>you.</em>
              </h2>
            </div>
            <Link className="pill" href="/book/scheduled">View all scheduled</Link>
          </div>
          <div className="pro-grid">
            {professionals.length === 0 ? <div className="empty-state">No verified professionals are available yet.</div> : professionals.map((professional) => (
              <Link className="pro-card" href={`/professionals/${professional.id}`} key={professional.name}>
                <div className={`pro-photo bg-linear-to-br ${professional.gradient}`}>
                  <div className="badge-row">
                    <span className="badge verified">Verified</span>
                    {professional.status === "Online now" && (
                      <span className="badge online">Online now</span>
                    )}
                  </div>
                  <span className="initials">{professional.initials}</span>
                </div>
                <div className="pro-body">
                  <h3>{professional.name}</h3>
                  <p>
                    {professional.role} · {professional.area}
                  </p>
                  <div className="pro-meta">
                    <strong>★ {professional.rating}</strong>
                    <span>
                      {professional.reviews} · {professional.experience}
                    </span>
                  </div>
                  <div className="pro-foot">
                    <span>
                      From {professional.price} <small>CAD</small>
                    </span>
                    <span className="btn btn-outline small">Book</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="dark-section" id="available">
          <div className="wrap section">
            <p className="eyebrow">
              <span>04 / 06</span> Instant booking
            </p>
            <div className="section-head">
              <h2>
                Available <em>now.</em>
              </h2>
              <p>
                Good things don&apos;t always need planning. See who has space today.
              </p>
              <Link className="pill" href="/book/instant">View all instant</Link>
            </div>
            <div className="now-list">
              {availableNow.length === 0 ? <div className="empty-state">No professionals are currently online. Try a scheduled booking.</div> : availableNow.map((professional) => (
                <article className="now-row" key={professional.name}>
                  <div className="now-left">
                    <span className={`now-avatar bg-linear-to-br ${professional.gradient}`}>
                      {professional.initials}
                    </span>
                    <div>
                      <h3>{professional.name}</h3>
                      <p>{professional.role}</p>
                    </div>
                  </div>
                  <div className="now-mid">
                    <span>{professional.nextTime}</span>
                    <span>{professional.distance}</span>
                  </div>
                  <Link className="btn btn-outline-light" href={`/professionals/${professional.id}`}>
                    Quick book
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="wrap section" id="professionals">
          <p className="eyebrow">
            <span>05 / 06</span> Simple by design
          </p>
          <h2>
            Good appointments<br />
            <em>start here.</em>
          </h2>
          <div className="steps">
            <article>
              <span>01</span>
              <h3>Customers book on web or app</h3>
              <p>
                Search first, sign up next, then pay with card authorization
                captured only after confirmed completion.
              </p>
            </article>
            <article>
              <span>02</span>
              <h3>Professionals operate in the app</h3>
              <p>
                Verification, online status, radius, calendar, GPS arrival, and
                job stages stay mobile-only for field work.
              </p>
            </article>
            <article>
              <span>03</span>
              <h3>Admins manage from the website</h3>
              <p>
                Verification review, live bookings, disputes, refunds,
                commissions, categories, and alerts stay in the dashboard.
              </p>
            </article>
          </div>
        </section>

        <section className="wrap section faq-section">
          <p className="eyebrow">
            <span>06 / 06</span> Good to know
          </p>
          <h2>
            Questions,<br />
            <em>answered.</em>
          </h2>
          {[
            "How are professionals verified?",
            "Can I book at home, office, hotel, or a senior's home?",
            "How are payments handled?",
            "What happens if a professional declines?",
          ].map((question, index) => (
            <details key={question} open={index === 0}>
              <summary>{question}</summary>
              <p>
                {index === 0
                  ? "Every professional submits ID, portfolio, experience details, and background verification before admin approval."
                  : "The platform keeps status, payment, notifications, and rematching visible so customers are never left guessing."}
              </p>
            </details>
          ))}
        </section>

        <section className="customer-app-band" id="download-app">
          <div className="wrap customer-app-content">
            <div>
              <p className="eyebrow"><span>Made for your pocket</span> Customer app</p>
              <h2>Book beautifully,<br /><em>wherever you are.</em></h2>
              <p>Download the Advoxy app for faster rebooking, live appointment updates, saved addresses, messages, and your complete booking history in one place.</p>
              <div className="customer-app-actions"><Link className="btn btn-primary" href="/signup">Create your account</Link><span>Available for iOS and Android</span></div>
            </div>
            <div className="customer-app-download">
              <div className="customer-phone"><div className="customer-phone-screen"><span className="phone-logo">advoxy</span><span className="customer-phone-kicker">YOUR NEXT APPOINTMENT</span><strong>Good afternoon.</strong><div className="customer-phone-qr"><div className="qr-code" aria-label="QR code placeholder for the Advoxy customer app">{customerQrPattern.map((row, rowIndex) => row.split("").map((cell, cellIndex) => <i className={cell === "1" ? "filled" : ""} key={`${rowIndex}-${cellIndex}`} />))}</div><span className="qr-caption">Scan to download</span></div><div className="customer-tabbar">Discover&nbsp;&nbsp;&nbsp; Bookings&nbsp;&nbsp;&nbsp; Profile</div></div></div>
            </div>
          </div>
        </section>
      </main>

    </>
  );
}
