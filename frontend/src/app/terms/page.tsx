import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="policy-page">
      <section className="wrap section">
        <p className="eyebrow">Advoxy terms</p>
        <h1>Terms of Service</h1>
        <p>
          These terms are a source-controlled placeholder for Advoxy&apos;s final
          legal terms. Replace this copy with counsel-approved terms before
          production launch.
        </p>
        <p>
          Customers must provide accurate booking details, professionals must
          honor accepted appointments, and all platform payments must be handled
          through Advoxy&apos;s configured payment provider.
        </p>
        <Link className="btn btn-primary" href="/signup">
          Back to signup
        </Link>
      </section>
    </main>
  );
}
