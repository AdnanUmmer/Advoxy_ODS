"use client";

import Script from "next/script";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, googleLogin } from "@/lib/api";

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleAccounts = {
  id: {
    initialize: (options: {
      client_id: string;
      callback: (response: GoogleCredentialResponse) => void;
    }) => void;
    renderButton: (
      parent: HTMLElement,
      options: { theme: "outline"; size: "large"; width?: number; text: "continue_with" }
    ) => void;
  };
};

type CredentialHandler = (response: GoogleCredentialResponse) => void;

let initializedGoogleClientId = "";
let activeCredentialHandler: CredentialHandler | null = null;

declare global {
  interface Window {
    google?: {
      accounts: GoogleAccounts;
    };
  }
}

export default function GoogleAuthButton({ role = "CUSTOMER" }: { role?: "CUSTOMER" | "PROFESSIONAL" }) {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const googleScriptUrl = process.env.NEXT_PUBLIC_GOOGLE_IDENTITY_SCRIPT_URL;
  const [message, setMessage] = useState(
    googleClientId && googleScriptUrl ? "" : "Google sign-in is currently unavailable. Please sign in with email."
  );
  const [scriptReady, setScriptReady] = useState(false);
  const [buttonReady, setButtonReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);

  const handleCredential = useCallback(async (response: GoogleCredentialResponse) => {
    if (submitting.current) return;
    if (!response.credential) {
      setMessage("Google did not return a sign-in credential.");
      return;
    }
    setMessage("");
    submitting.current = true;
    setBusy(true);
    try {
      const user = await googleLogin({ credential: response.credential, role });
      const next = new URLSearchParams(window.location.search).get("next");
      const destination = next && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\") ? next : null;
      router.replace(destination || (user.role === "ADMIN" ? "/admin" : user.role === "PROFESSIONAL" ? "/vendor" : "/dashboard"));
    } catch (error) {
      setMessage(error instanceof ApiError ? "Google sign-in could not be completed. Please try again or sign in with email." : "Unable to connect. Please check your connection and try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }, [role, router]);

  useEffect(() => {
    if (!scriptReady || !googleClientId || !googleScriptUrl || !buttonRef.current || !window.google) return;
    buttonRef.current.innerHTML = "";
    activeCredentialHandler = (response) => {
      void handleCredential(response);
    };
    if (initializedGoogleClientId !== googleClientId) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => {
          activeCredentialHandler?.(response);
        },
      });
      initializedGoogleClientId = googleClientId;
    }
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      text: "continue_with",
      width: 280,
    });
    setButtonReady(true);
  }, [googleClientId, googleScriptUrl, scriptReady, handleCredential]);

  return (
    <div className="social-auth">
      {googleClientId && googleScriptUrl && <Script src={googleScriptUrl} onReady={() => setScriptReady(true)} onError={() => setMessage("Google sign-in could not load. Please refresh or sign in with email.")} />}
      <div className="divider"><span>or</span></div>
      <div aria-busy={busy} style={{ minHeight: 44 }}>
        <div ref={buttonRef} className="google-button-slot" aria-label="Continue with Google" inert={busy} />
        {!buttonReady && !message && <p role="status">Loading Google sign-in...</p>}
      </div>
      {busy && <p role="status">Signing you in...</p>}
      {message && <p className="form-message error" role="alert">{message}</p>}
    </div>
  );
}
