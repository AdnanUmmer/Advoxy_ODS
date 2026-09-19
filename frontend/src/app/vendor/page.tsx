"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Booking, bookingAction, getProfessionalDashboard, getMe, logout, Professional } from "@/lib/api";
import ProfessionalServicesPanel from "./ProfessionalServicesPanel";

function label(value: string) { return value.toLowerCase().replaceAll("_", " "); }

export default function VendorPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Professional | null>(null);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("advoxy_token")) { router.push("/login"); return; }
    Promise.all([getMe(), getProfessionalDashboard()]).then(([user, data]) => {
      if (user.role !== "PROFESSIONAL") { router.push("/dashboard"); return; }
      setProfile(data.profile);
      setBookings(data.bookings);
    }).catch(() => setMessage("We could not load your professional workspace."));
  }, [router]);

  async function updateBooking(id: number, action: string) {
    try {
      const booking = await bookingAction(id, action, action === "decline" ? { reason: "Professional unavailable." } : {});
      setBookings((current) => current.map((item) => item.id === id ? booking : item));
    } catch { setMessage("That appointment changed or is no longer available."); }
  }

  async function handleLogout() { try { await logout(); } finally { router.push("/"); } }

  if (message) return <main className="centered-state"><p className="eyebrow">Professional workspace</p><h1>{message}</h1><Link className="btn btn-primary" href="/login">Return to login</Link></main>;
  if (!profile) return <main className="centered-state"><p className="eyebrow">Professional workspace</p><h1>Loading your appointments...</h1></main>;

  return <><header className="admin-topbar"><Link href="/" className="logo">advoxy <sup>®</sup></Link><span>Professional workspace</span><button className="text-action" onClick={handleLogout}>Log out</button></header><main className="dashboard-shell"><div className="dashboard-heading"><div><p className="eyebrow"><span>Professional / today</span></p><h1>Welcome, <em>{profile.display_name}.</em></h1><p className="lead">Manage your appointments and keep your availability current.</p></div><span className={`status-pill ${profile.is_active ? "confirmed" : "no_match"}`}>{profile.is_active ? "Verified profile" : "Verification pending"}</span></div><section className="dashboard-stats"><article><span>Rating</span><strong>{profile.average_rating ?? "New"}</strong></article><article><span>Reviews</span><strong>{profile.review_count}</strong></article><article><span>Experience</span><strong>{profile.years_experience} yrs</strong></article></section><section className="dashboard-section"><p className="eyebrow">Assigned appointments</p><h2>Your calendar</h2>{bookings.length === 0 ? <div className="empty-state">No assigned appointments yet.</div> : <div className="booking-list">{bookings.map((booking) => <article className="booking-row" key={booking.id}><div><span className="booking-id">Booking #{booking.id}</span><h3>{booking.booking_type.toLowerCase()} appointment</h3><p>{booking.scheduled_time ? new Date(booking.scheduled_time).toLocaleString() : "Instant request"}</p></div><div className="booking-row-end"><span className={`status-pill ${booking.status.toLowerCase()}`}>{label(booking.status)}</span>{booking.status === "PENDING_ACCEPT" && <div><button className="text-action" onClick={() => updateBooking(booking.id, "accept")}>Accept</button><button className="text-action" onClick={() => updateBooking(booking.id, "decline")}>Decline</button></div>}{booking.status === "CONFIRMED" && <button className="text-action" onClick={() => updateBooking(booking.id, "start")}>Start work</button>}{booking.status === "STARTED" && <button className="text-action" onClick={() => updateBooking(booking.id, "complete")}>Mark complete</button>}</div></article>)}</div>}</section><ProfessionalServicesPanel /></main></>;
}
