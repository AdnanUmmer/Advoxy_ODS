"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import GoogleAuthButton from "@/components/GoogleAuthButton";
import { ApiError, login } from "@/lib/api";

export default function LoginForm() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "submitting" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await login({
        username: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
      });
      const next = new URLSearchParams(window.location.search).get("next");
      router.push(next || (response.role === "ADMIN" ? "/admin" : response.role === "PROFESSIONAL" ? "/vendor" : "/dashboard"));
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof ApiError ? "Email or password is incorrect." : "Could not reach the API. Start Django and try again.");
    }
  }

  return (
    <div className="login-container">
      <form onSubmit={handleSubmit}>
        <label className="field"><span>Email</span><input name="email" type="email" placeholder="you@email.com" required /></label>
        <label className="field"><span>Password</span><input name="password" type="password" required /></label>
        <button className="submit-btn" type="submit" disabled={status === "submitting"}>{status === "submitting" ? "Signing in..." : "Log in"}</button>
        {message && <p className="form-message error">{message}</p>}
      </form>
      <GoogleAuthButton role="CUSTOMER" />
    </div>
  );
}
