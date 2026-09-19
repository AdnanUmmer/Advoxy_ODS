import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="policy-page">
      <section className="wrap section">
        <p className="eyebrow">Advoxy privacy</p>
        <h1>Privacy Policy</h1>
        <p>
          This policy page is a source-controlled placeholder for Advoxy&apos;s
          final privacy policy. Replace this copy with counsel-approved privacy
          terms before production launch.
        </p>
        <p>
          Advoxy stores account, booking, location, payment status, messaging,
          and verification workflow data needed to operate the marketplace.
          Public professional profiles must never expose private identity
          documents, personal contact details, or background-check records.
        </p>
        <Link className="btn btn-primary" href="/signup">
          Back to signup
        </Link>
      </section>
    </main>
  );
}
