import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SignupForm from "./SignupForm";

export default function SignupPage() {
  return (
    <>
      <SiteHeader />

      <main className="signup-layout signup-simple-layout">
        <section className="form-panel" aria-label="Create customer account">
          <div className="form-wrap">
            <div className="tabs" role="tablist" aria-label="Account action">
              <button className="active" type="button">
                Sign up
              </button>
              <Link className="tab" href="/login">Log in</Link>
            </div>

            <SignupForm />

            <p className="switch-line">
              Already have an account? <Link href="/login">Log in</Link>
            </p>
          </div>
        </section>
      </main>
    </>
  );
}
