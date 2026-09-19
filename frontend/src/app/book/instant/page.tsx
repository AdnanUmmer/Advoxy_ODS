"use client";

import { useEffect, useState } from "react";
import { getProfessionals, Professional } from "@/lib/api";
import ProfessionalCard from "@/components/ProfessionalCard";
import SiteHeader from "@/components/SiteHeader";

export default function InstantBookingPage() {
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function fetchInstants() {
      try {
        // We use availableNow: true to get online professionals
        const results = await getProfessionals({
          availableNow: true,
          bookingType: "INSTANT"
        });
        setProfessionals(results);
        setState("ready");
      } catch {
        setState("error");
        setMessage("Could not reach the marketplace API.");
      }
    }
    fetchInstants();
  }, []);

  return (
    <>
      <SiteHeader />
      <div className="nav-spacer" />

      <main className="wrap instant-page">
        <section className="instant-hero">
          <div>
            <p className="eyebrow"><span>Instant booking</span> Calgary</p>
            <h1>Good work, <em>right now.</em></h1>
            <p className="lead">Browse verified professionals who are online and ready to accept an appointment immediately.</p>
          </div>
          <div className="instant-promise"><strong>Ready when you are</strong><span>Choose a professional, confirm your address, and authorize payment securely.</span></div>
        </section>

        <div className="instant-toolbar">
          <div><strong>{state === "ready" ? professionals.length : "..."}</strong><span>professionals available now</span></div>
          <span className="instant-status"><i /> Live availability</span>
        </div>

        <div className="result-list" aria-live="polite">
          {state === "error" ? (
            <div className="empty-state error-state">{message}</div>
          ) : state === "loading" ? (
            <div className="empty-state">Finding online professionals...</div>
          ) : state === "ready" && professionals.length === 0 ? (
            <div className="empty-state instant-empty">
              <span className="empty-icon" aria-hidden="true">◷</span>
              <h2>No one is available right now</h2>
              <p>Try a scheduled booking and choose a time that works for you.</p>
              <a className="btn btn-primary small" href="/search?booking_type=SCHEDULED">Browse scheduled times</a>
            </div>
          ) : (
            professionals.map((professional) => (
              <ProfessionalCard key={professional.id} professional={professional} />
            ))
          )}
        </div>
        {state === "error" && <button className="btn btn-outline instant-retry" type="button" onClick={() => window.location.reload()}>Try again</button>}
      </main>
    </>
  );
}
