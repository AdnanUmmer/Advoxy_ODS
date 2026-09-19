"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, requestPasswordReset } from "@/lib/api";
import SiteHeader from "@/components/SiteHeader";

export default function ForgotPasswordPage() {
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");
    const email = String(new FormData(event.currentTarget).get("email") ?? "");
    try {
      const result = await requestPasswordReset(email);
      setStatus("success");
      setMessage(result.detail);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof ApiError ? "We could not process that request." : "The API is unavailable right now.");
    }
  }

  return (
    <>
      <SiteHeader />
      <main className="auth-layout"><section className="auth-intro"><p className="eyebrow">Account recovery</p><h1>A quiet way back to your <em>account.</em></h1><p className="lead">We will send a single-use reset link to the email on your account.</p></section><section className="form-panel"><div className="form-wrap"><p className="eyebrow">Forgot password</p><h2 className="auth-form-title">Reset your password</h2><form onSubmit={submit}><label className="field"><span>Email</span><input name="email" type="email" placeholder="you@email.com" required /></label><button className="submit-btn" type="submit" disabled={status === "submitting"}>{status === "submitting" ? "Sending link..." : "Send reset link"}</button>{message && <p className={`form-message ${status}`}>{message}</p>}</form><p className="switch-line"><Link href="/login">Return to login</Link></p></div></section></main>
    </>
  );
}
