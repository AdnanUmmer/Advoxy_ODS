"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent } from "react";
import { useEffect, useState } from "react";
import { AdminCatalog, AdminDashboard, AUTH_BASE_URL, getAdminCatalog, getAdminDashboard, getMarketplaceSettings, getMe, logout, MarketplaceSettings, updateAdminCatalog, updateMarketplaceSettings } from "@/lib/api";

const cards = [
  ["customers", "Customers"],
  ["professionals", "Professionals"],
  ["bookings", "All bookings"],
  ["today_bookings", "Today"],
  ["pending_verifications", "Pending verification"],
  ["pending_payments", "Held payments"],
];

export default function AdminPage() {
  const router = useRouter();
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [message, setMessage] = useState("");
  const [settings, setSettings] = useState<MarketplaceSettings | null>(null);
  const [settingsMessage, setSettingsMessage] = useState("");
  const [catalog, setCatalog] = useState<AdminCatalog | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("advoxy_token")) {
      router.push("/login");
      return;
    }
    Promise.all([getMe(), getAdminDashboard(), getMarketplaceSettings(), getAdminCatalog()])
      .then(([user, dashboard, marketplaceSettings, adminCatalog]) => {
        if (user.role !== "ADMIN") {
          router.push("/dashboard");
          return;
        }
        setData(dashboard);
        setSettings(marketplaceSettings);
        setCatalog(adminCatalog);
      })
      .catch(() => setMessage("Administrator access could not be verified."));
  }, [router]);

  async function handleLogout() {
    try { await logout(); } finally { router.push("/"); }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    try {
      setSettingsMessage("Saving settings...");
      setSettings(await updateMarketplaceSettings(settings));
      setSettingsMessage("Settings saved.");
    } catch {
      setSettingsMessage("Settings could not be saved. Check the values and try again.");
    }
  }

  async function saveDuration(serviceId: number, duration: number) {
    try {
      await updateAdminCatalog({ service_id: serviceId, duration_minutes: duration });
      setSettingsMessage("Service duration saved.");
    } catch {
      setSettingsMessage("Service duration could not be saved.");
    }
  }

  async function savePrice(serviceId: number, price: number) {
    try {
      await updateAdminCatalog({ professional_service_id: serviceId, price });
      setSettingsMessage("Service price saved.");
    } catch {
      setSettingsMessage("Service price could not be saved.");
    }
  }

  if (message) return <main className="centered-state"><p className="eyebrow">Control center</p><h1>{message}</h1><Link className="btn btn-primary" href="/">Return home</Link></main>;
  if (!data) return <main className="centered-state"><p className="eyebrow">Control center</p><h1>Loading platform overview...</h1></main>;

  return (
    <>
      <header className="admin-topbar">
        <Link href="/" className="logo">
          advoxy <sup>®</sup>
        </Link>
        <span>Operations control center</span>
        <button className="text-action" onClick={handleLogout}>Log out</button>
      </header>
      <main className="admin-layout">
        <aside className="admin-sidebar">
          <p className="sidebar-label">Workspace</p>
          <Link className="active" href="/admin">Overview</Link>
          <a href="#bookings">Bookings</a>
          <a href="#catalog">Catalog</a>
          <p className="sidebar-label">System</p>
          <a href="#verification">Verification queue</a>
        </aside>
        <section className="admin-content">
          <div className="admin-heading">
            <div>
              <p className="eyebrow">
                <span>Admin / overview</span>
              </p>
              <h1>Good morning, <em>operator.</em></h1>
              <p className="lead">A live view of the marketplace and the work that needs attention.</p>
            </div>
            <button className="btn btn-outline" onClick={() => window.location.reload()}>
              Refresh data
            </button>
          </div>

          <section className="admin-stats">
            {cards.map(([key, label]) => (
              <article key={key}>
                <span>{label}</span>
                <strong>{data.counts[key] ?? 0}</strong>
              </article>
            ))}
          </section>

          <div className="admin-grid">
            <article className="admin-panel" id="bookings">
              <div className="admin-panel-head">
                <div>
                  <p className="eyebrow">Live operations</p>
                  <h2>Recent bookings</h2>
                </div>
                <Link href="/dashboard">Customer view</Link>
              </div>
              {data.recent_bookings.length === 0 ? (
                <div className="empty-state">No bookings yet.</div>
              ) : (
                <div className="admin-table">
                  {data.recent_bookings.map((booking) => (
                    <div className="admin-table-row" key={booking.id}>
                      <div>
                        <strong>#{booking.id}</strong>
                        <span>{booking.booking_type.toLowerCase()} booking</span>
                      </div>
                      <span className={`status-pill ${booking.status.toLowerCase()}`}>
                        {booking.status.toLowerCase().replaceAll("_", " ")}
                      </span>
                      <strong>${Number.parseFloat(booking.total_amount).toFixed(2)}</strong>
                    </div>
                  ))}
                </div>
              )}
            </article>

            <article className="admin-panel" id="catalog">
              <p className="eyebrow">Marketplace health</p>
              <h2>Catalog pulse</h2>
              <div className="pulse-list">
                <div>
                  <span>Active categories</span>
                  <strong>{data.counts.categories}</strong>
                </div>
                <div>
                  <span>Active services</span>
                  <strong>{data.counts.services}</strong>
                </div>
                <div>
                  <span>Verified professionals</span>
                  <strong>{data.counts.active_professionals}</strong>
                </div>
                <div>
                  <span>Reviews received</span>
                  <strong>{data.counts.reviews}</strong>
                </div>
              </div>
            </article>
          </div>

          <section className="admin-panel" id="verification" style={{ marginTop: "18px" }}>
            <div className="admin-panel-head">
              <div>
                <p className="eyebrow">Needs attention</p>
                <h2>Verification queue</h2>
              </div>
              <span className="status-pill pending_accept">{data.counts.pending_verifications} pending</span>
            </div>
            <p className="admin-muted">
              Review applicant identity and background outcomes in the secure Django admin workflow until the dedicated verification console is connected.
            </p>
            <a className="btn btn-outline small" href={`${AUTH_BASE_URL}/admin/`} target="_blank" rel="noreferrer">
              Open secure admin
            </a>
          </section>
          {settings && <section className="admin-panel" id="settings" style={{ marginTop: "18px" }}>
            <div className="admin-panel-head"><div><p className="eyebrow">Settings</p><h2>Marketplace rules</h2></div><span>{settingsMessage}</span></div>
            <form className="admin-settings-form" onSubmit={saveSettings}>
              {[
                ["instant_initial_radius_km", "Instant initial radius (km)"],
                ["instant_max_radius_km", "Instant maximum radius (km)"],
                ["scheduled_search_radius_km", "Scheduled search radius (km)"],
                ["radius_expansion_step_km", "Radius expansion step (km)"],
                ["professional_service_radius_km", "Default professional radius (km)"],
                ["maximum_travel_distance_km", "Maximum travel distance (km)"],
                ["included_travel_distance_km", "Included travel distance (km)"],
                ["travel_fee_per_km", "Travel fee per km"],
                ["maximum_travel_fee", "Maximum travel fee"],
                ["minimum_booking_price", "Minimum booking price"],
                ["commission_percent", "Platform commission (%)"],
                ["fixed_platform_fee", "Fixed platform fee"],
                ["minimum_platform_fee", "Minimum platform fee"],
                ["maximum_platform_fee", "Maximum platform fee"],
                ["customer_cancellation_window_minutes", "Customer cancellation window (minutes)"],
                ["professional_acceptance_window_minutes", "Professional acceptance window (minutes)"],
                ["scheduled_minimum_notice_minutes", "Scheduled minimum notice (minutes)"],
                ["maximum_advance_booking_days", "Maximum advance booking (days)"],
                ["instant_booking_timeout_minutes", "Instant booking timeout (minutes)"],
                ["rematching_timeout_minutes", "Rematching timeout (minutes)"],
                ["reminder_minutes_before_booking", "Reminder timing (minutes)"],
                ["availability_weight", "Availability ranking weight"],
                ["distance_weight", "Distance ranking weight"],
                ["rating_weight", "Rating ranking weight"],
                ["review_count_weight", "Review count ranking weight"],
                ["experience_weight", "Experience ranking weight"],
                ["reliability_weight", "Reliability ranking weight"],
              ].map(([key, label]) => <label key={key}><span>{label}</span><input type="number" min="0" step="0.01" value={String(settings[key] ?? "")} onChange={(event) => setSettings({ ...settings, [key]: Number(event.target.value) })} /></label>)}
              {[["instant_booking_enabled", "Instant booking enabled"], ["scheduled_booking_enabled", "Scheduled booking enabled"], ["multiple_service_booking_enabled", "Multiple-service booking enabled"], ["travel_fees_enabled", "Travel fees enabled"], ["rematching_enabled", "Professional rematching enabled"], ["tax_enabled", "Tax enabled"]].map(([key, label]) => <label key={key}><span>{label}</span><input type="checkbox" checked={Boolean(settings[key])} onChange={(event) => setSettings({ ...settings, [key]: event.target.checked })} /></label>)}
              <label><span>Tax name</span><input value={String(settings.tax_name ?? "")} onChange={(event) => setSettings({ ...settings, tax_name: event.target.value })} /></label>
              <label><span>Tax percentage</span><input type="number" min="0" max="100" step="0.01" value={String(settings.tax_percent ?? "")} onChange={(event) => setSettings({ ...settings, tax_percent: Number(event.target.value) })} /></label>
              <button className="btn btn-primary" type="submit">Save marketplace settings</button>
            </form>
          </section>}
          {catalog && <section className="admin-panel" style={{ marginTop: "18px" }}>
            <div className="admin-panel-head"><div><p className="eyebrow">Catalog</p><h2>Service durations</h2></div></div>
            <div className="pulse-list">{catalog.services.map((service) => <div key={service.id}><span>{service.name}</span><label><input aria-label={`${service.name} duration`} type="number" min="1" max="480" defaultValue={service.duration_minutes} onBlur={(event) => void saveDuration(service.id, Number(event.target.value))} /> min</label></div>)}</div>
            <h3>Professional prices</h3>
            <div className="pulse-list">{catalog.professional_services.map((service) => <div key={service.id}><span>{service.professional_name} · {service.service_name}</span><label>$<input aria-label={`${service.professional_name} ${service.service_name} price`} type="number" min="0" step="0.01" defaultValue={service.price} onBlur={(event) => void savePrice(service.id, Number(event.target.value))} /></label></div>)}</div>
          </section>}
        </section>
      </main>
    </>
  );
}
