import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <>
      <SiteHeader />
      <main className="auth-layout">
        <section className="auth-intro">
          <p className="eyebrow">Welcome back</p>
          <h1>Your next good appointment is <em>close.</em></h1>
          <p className="lead">Sign in to manage upcoming visits, saved addresses, and booking updates.</p>
        </section>
        <section className="form-panel" aria-label="Log in">
          <div className="form-wrap">
            <div className="tabs"><Link href="/signup">Sign up</Link><span className="active">Log in</span></div>
            <LoginForm />
            <Link className="forgot-link" href="/forgot-password">Forgot your password?</Link>
            <p className="switch-line">New to Advoxy? <Link href="/signup">Create an account</Link></p>
          </div>
        </section>
      </main>
    </>
  );
}
