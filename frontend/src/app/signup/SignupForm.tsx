"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import GoogleAuthButton from "@/components/GoogleAuthButton";
import { ApiError, signup } from "@/lib/api";

export default function SignupForm() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  function splitName(fullName: string) {
    const [firstName, ...rest] = fullName.trim().split(/\s+/);
    return {
      first_name: firstName ?? "",
      last_name: rest.join(" "),
    };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");

    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const passwordConfirm = String(form.get("password_confirm") ?? "");
    const fullName = String(form.get("full_name") ?? "");

    if (password !== passwordConfirm) {
      setStatus("error");
      setMessage("Passwords do not match.");
      return;
    }

    try {
      await signup({
        email,
        password,
        ...splitName(fullName),
        phone_number: String(form.get("phone_number") ?? ""),
        date_of_birth: String(form.get("date_of_birth") ?? ""),
        role: "CUSTOMER",
      });

      setStatus("success");
      setMessage("Account created. Taking you to booking setup...");
      const next = new URLSearchParams(window.location.search).get("next");
      window.setTimeout(() => router.push(next || "/book"), 450);
    } catch (error) {
      setStatus("error");
      setMessage(
        error instanceof ApiError
          ? "Signup failed. Please check your details and try again."
          : "Could not reach the API. Start the Django backend and try again."
      );
    }
  }

  return (
    <div className="login-container">
    <form onSubmit={handleSubmit}>
      <label className="field">
        <span>Full name</span>
        <input name="full_name" type="text" placeholder="Jordan Lee" required />
      </label>

      <div className="field-row">
        <label className="field">
          <span>Email</span>
          <input name="email" type="email" placeholder="you@email.com" required />
        </label>
        <label className="field">
          <span>Phone</span>
          <input name="phone_number" type="tel" placeholder="(403) 555-0132" required />
        </label>
      </div>

      <label className="field">
        <span>Date of birth</span>
        <input name="date_of_birth" type="date" required />
        <small>You must be 18 or older to book on Advoxy.</small>
      </label>

      <label className="field">
        <span>Password</span>
        <input name="password" type="password" placeholder="At least 8 characters" minLength={8} required />
      </label>

      <label className="field">
        <span>Confirm Password</span>
        <input name="password_confirm" type="password" placeholder="Repeat password" required />
      </label>

      <label className="checkbox-row">
        <input type="checkbox" required />
        <span>
          I agree to Advoxy&apos;s <Link href="/terms">Terms of Service</Link> and{" "}
          <Link href="/privacy">Privacy Policy</Link>.
        </span>
      </label>

      <button className="submit-btn" type="submit" disabled={status === "submitting"}>
        {status === "submitting" ? "Creating account..." : "Create customer account"}
      </button>

      {message && <p className={`form-message ${status}`}>{message}</p>}
    </form>
      <GoogleAuthButton role="CUSTOMER" />
    </div>
  );
}
