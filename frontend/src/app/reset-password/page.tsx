"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { ApiError, confirmPasswordReset } from "@/lib/api";
import SiteHeader from "@/components/SiteHeader";

function ResetForm() {
  const params = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    if (password !== String(form.get("password_confirm") ?? "")) {
      setStatus("error");
      setMessage("Passwords do not match.");
      return;
    }
    setStatus("submitting");
    try {
      const result = await confirmPasswordReset({ uid: Number(params.get("uid")), token: params.get("token") ?? "", new_password: password });
      setStatus("success");
      setMessage(result.detail);
      window.setTimeout(() => router.push("/login"), 700);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof ApiError ? "This reset link is invalid or expired." : "The API is unavailable right now.");
    }
  }

  return <form onSubmit={submit}><label className="field"><span>New password</span><input name="password" type="password" minLength={8} required /></label><label className="field"><span>Confirm password</span><input name="password_confirm" type="password" minLength={8} required /></label><button className="submit-btn" type="submit" disabled={status === "submitting"}>{status === "submitting" ? "Updating password..." : "Set new password"}</button>{message && <p className={`form-message ${status}`}>{message}</p>}</form>;
}

export default function ResetPasswordPage() {
  return <><SiteHeader /><main className="auth-layout"><section className="auth-intro"><p className="eyebrow">Account recovery</p><h1>Choose a password that feels <em>secure.</em></h1></section><section className="form-panel"><div className="form-wrap"><p className="eyebrow">Reset password</p><h2 className="auth-form-title">Set a new password</h2><Suspense fallback={<p className="empty-state">Loading reset form...</p>}><ResetForm /></Suspense></div></section></main></>;
}
