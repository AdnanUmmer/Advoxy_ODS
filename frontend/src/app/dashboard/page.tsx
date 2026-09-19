"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Booking, cancelBooking, Conversation, getBookings, getConversations, getFavorites, getMe, getNotifications, BookingNotification, markConversationRead, sendConversationMessage, Professional } from "@/lib/api";

function statusLabel(status: string) {
  return status.toLowerCase().replaceAll("_", " ");
}

export default function DashboardPage() {
  const router = useRouter();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [user, setUser] = useState<{ first_name: string; email: string } | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [notifications, setNotifications] = useState<BookingNotification[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState("");
  const [chatState, setChatState] = useState<"idle" | "sending" | "error">("idle");
  const [favorites, setFavorites] = useState<Professional[]>([]);

  useEffect(() => {
    if (!localStorage.getItem("advoxy_token")) {
      router.push("/login");
      return;
    }
    Promise.all([getBookings(), getMe(), getNotifications(), getConversations(), getFavorites()])
      .then(([nextBookings, userData, nextNotifications, nextConversations, nextFavorites]) => {
        setBookings(nextBookings);
        setUser(userData);
        setNotifications(nextNotifications);
        setConversations(nextConversations);
        setFavorites(nextFavorites);
        setState("ready");
      })
      .catch(() => {
        setState("error");
        setMessage("We could not load your account. Please sign in again.");
      });
  }, [router]);

  async function handleCancel(id: number) {
    if (!window.confirm("Cancel this booking?")) return;
    try {
      const updated = await cancelBooking(id);
      setBookings((current) => current.map((booking) => booking.id === id ? updated : booking));
    } catch {
      setMessage("This booking can no longer be cancelled.");
    }
  }

  async function openChat(bookingId: number) {
    const conversation = conversations.find((item) => item.booking === bookingId);
    if (!conversation) {
      setMessage("Chat is not available until a professional is assigned.");
      return;
    }
    setActiveConversation(conversation);
    await markConversationRead(conversation.id).catch(() => undefined);
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeConversation || !draft.trim()) return;
    setChatState("sending");
    try {
      const sent = await sendConversationMessage(activeConversation.id, draft.trim());
      setActiveConversation((current) => current ? { ...current, messages: [...current.messages, sent] } : current);
      setDraft("");
      setChatState("idle");
    } catch {
      setChatState("error");
    }
  }

  if (state === "error") return <main className="centered-state"><p className="eyebrow">Account</p><h1>{message}</h1><Link className="btn btn-primary" href="/login">Log in again</Link></main>;

  const upcoming = bookings.filter((booking) => !["CONFIRMED_COMPLETE", "CANCELLED_CUSTOMER", "CANCELLED_PROFESSIONAL", "NO_MATCH"].includes(booking.status));
  const past = bookings.filter((booking) => !upcoming.includes(booking));

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="logo">advoxy <sup>®</sup></div>
        <ul className="side-nav">
          <li><a className="active" href="/dashboard"><span className="dot"></span>Appointments</a></li>
          <li><a href="/search"><span className="dot"></span>Discover</a></li>
          <li><span className="side-nav-disabled"><span className="dot"></span>Favorites</span></li>
          <li><span className="side-nav-disabled"><span className="dot"></span>Messages</span></li>
          <li><span className="side-nav-disabled"><span className="dot"></span>Payment methods</span></li>
          <li><span className="side-nav-disabled"><span className="dot"></span>Settings</span></li>
        </ul>
        <div className="side-foot">
          <div className="side-avatar">{user?.first_name ? user.first_name[0].toUpperCase() : "U"}</div>
          <div>
            <div className="name">{user?.first_name || "User"}</div>
            <div className="email">{user?.email}</div>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="page-head">
          <div>
            <h1>Good afternoon, <em>{user?.first_name || "there"}.</em></h1>
            <p>You have {upcoming.length} appointment{upcoming.length !== 1 ? "s" : ""} coming up this week.</p>
          </div>
          <Link className="btn btn-primary" href="/book">Book something new</Link>
        </div>

        <div className="section-label">Upcoming</div>
        {state === "loading" ? <div className="empty-state">Loading your appointments...</div> : upcoming.length === 0 ? (
          <div className="empty-state">No upcoming appointments yet. Your next good appointment is close.</div>
        ) : (
          <div className="upcoming-list">
            {upcoming.map((booking) => (
              <div className="appt-card" key={booking.id}>
                <div className="appt-date">
                  <div className="day">{booking.scheduled_time ? new Date(booking.scheduled_time).getDate() : "??"}</div>
                  <div className="mon">{booking.scheduled_time ? new Date(booking.scheduled_time).toLocaleString('default', { month: 'short' }) : "TBD"}</div>
                </div>
                <div>
                  <div className="appt-service">{booking.booking_type === "INSTANT" ? "Instant visit" : "Scheduled visit"}</div>
                  <div className="appt-with">Booking #{booking.id} · {booking.scheduled_time ? new Date(booking.scheduled_time).toLocaleDateString() : "TBD"}</div>
                  <div className="appt-time">{booking.scheduled_time ? new Date(booking.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Finding match..."}</div>
                </div>
                <div className="appt-actions">
                  <button className="btn btn-outline small" onClick={() => handleCancel(booking.id)}>Cancel</button>
                  <button className="btn btn-outline small" onClick={() => void openChat(booking.id)}>Chat</button>
                  <Link className="btn btn-outline small" href={`/book?bookingId=${booking.id}`}>Manage</Link>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="section-label">Past appointments</div>
        {past.length === 0 ? (
          <div className="empty-state">Completed visits will appear here.</div>
        ) : (
          <div className="past-list">
            {past.map((booking) => (
              <div className="past-row" key={booking.id}>
                <div className="past-left">
                  <div className="past-avatar">{booking.booking_type === "INSTANT" ? "I" : "S"}</div>
                  <div>
                    <div className="past-service">{booking.booking_type === "INSTANT" ? "Instant visit" : "Scheduled visit"}</div>
                    <div className="past-meta">Booking #{booking.id} · {booking.status === "CONFIRMED_COMPLETE" ? "Completed" : statusLabel(booking.status)}</div>
                  </div>
                </div>
                <div className="past-right">
                  <span className="rebook-link" style={{ cursor: "pointer" }} onClick={() => router.push("/book")}>Rebook</span>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="section-label">Your favorites</div>
        <div className="fav-grid">
          {favorites.length === 0 ? <div className="empty-state" style={{ gridColumn: "1/-1", textAlign: "center" }}>Your favorite professionals will appear here.</div> : favorites.map((favorite) => <Link className="favorite-dashboard-card" href={`/professionals/${favorite.id}`} key={favorite.id}><span>{favorite.display_name.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span><div><strong>{favorite.display_name}</strong><small>{favorite.services[0]?.name || "Beauty professional"} · {favorite.area || "Calgary"}</small></div></Link>)}
        </div>
        <div className="section-label">Notifications</div>
        <div className="notification-list">
          {notifications.length === 0 ? <div className="empty-state">Booking updates will appear here.</div> : notifications.slice(0, 8).map((notification) => <div className="notification-row" key={notification.id}><strong>{statusLabel(notification.event)}</strong><span>{notification.body}</span></div>)}
        </div>
        {activeConversation && <div className="chat-panel" aria-label="Booking chat">
          <div className="section-label">Booking #{activeConversation.booking} chat</div>
          <div className="chat-messages">{activeConversation.messages.length === 0 ? <div className="empty-state">No messages yet.</div> : activeConversation.messages.map((chatMessage) => <div className="chat-message" key={chatMessage.id}><strong>{chatMessage.sender_name || "Participant"}</strong><span>{chatMessage.body}</span></div>)}</div>
          <form onSubmit={sendMessage}><input aria-label="Message" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a message" /><button className="btn btn-primary" type="submit" disabled={chatState === "sending"}>{chatState === "sending" ? "Sending..." : "Send"}</button></form>
          {chatState === "error" && <p className="form-message error">Message could not be sent.</p>}
        </div>}
      </main>
    </div>
  );
}
