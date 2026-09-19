"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { getMe, logout } from "@/lib/api";

export default function SiteHeader({ hideSignup = false }: { hideSignup?: boolean }) {
  const router = useRouter();
  const [user, setUser] = useState<{ first_name: string; last_name: string; email: string; role: string } | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!localStorage.getItem("advoxy_token")) return;
    getMe().then(setUser).catch(() => {
      localStorage.removeItem("advoxy_token");
      setUser(null);
    });
  }, []);

  useEffect(() => {
    function closeMenu(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, []);

  const initials = user
    ? `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase() || user.email[0].toUpperCase()
    : "";
  const dashboard = user?.role === "PROFESSIONAL" ? "/vendor" : user?.role === "ADMIN" ? "/admin" : "/dashboard";

  async function signOut() {
    try { await logout(); } finally {
      setUser(null);
      setOpen(false);
      router.push("/");
    }
  }

  return (
    <header className="wrap">
      <nav className="floating-nav" aria-label="Primary navigation">
        <Link href="/" className="logo">advoxy <sup>®</sup></Link>
        <div className="nav-links">
          <Link href="/#discover">Discover</Link>
          <Link href="/#services">Services</Link>
          <Link href="/book/instant">Available now</Link>
          <Link href="/professionals">For professionals</Link>
        </div>
        <div className="nav-actions">
          {user ? (
            <div className="account-menu" ref={menuRef}>
              <button className="account-trigger" type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
                <span className="account-avatar" aria-hidden="true">{initials}</span>
                <span className="account-label">{user.first_name || "Account"}</span>
                <span className="account-chevron" aria-hidden="true">⌄</span>
              </button>
              {open && (
                <div className="account-popover">
                  <div className="account-summary"><strong>{user.first_name} {user.last_name}</strong><span>{user.email}</span></div>
                  <Link href={dashboard} onClick={() => setOpen(false)}>My {user.role === "PROFESSIONAL" ? "workspace" : "bookings"}</Link>
                  <Link href="/services" onClick={() => setOpen(false)}>Book a service</Link>
                  <button type="button" onClick={() => void signOut()}>Log out</button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link className="login-link" href="/login">Log in</Link>
              {!hideSignup && <Link className="btn btn-primary small" href="/signup">Sign up</Link>}
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
