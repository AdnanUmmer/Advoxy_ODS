import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";

export const metadata = {
  title: "Become an Advoxy professional",
  description: "Join Advoxy as an independent hair or nail professional.",
};

export default function ProfessionalsPage() {
  const steps = [
    ["01", "Download the app", "Professional onboarding and account creation happen in the Advoxy mobile app."],
    ["02", "Build your profile", "Add your craft, services, pricing, service area, and the hours that suit you."],
    ["03", "Get verified", "Submit your identity and experience for review before you appear to customers."],
    ["04", "Work on your terms", "Choose when you are online, accept the right bookings, and keep every handoff visible."],
  ];
  const qrPattern = [
    "111111100101111",
    "100000101001001",
    "101110100111101",
    "101110101010101",
    "101110100110101",
    "100000101010001",
    "111111101010111",
    "000000001101000",
    "110111111001101",
    "001001001111010",
    "111101110100111",
    "100010011011001",
    "101110111110101",
    "100000100010001",
    "111111101110111",
  ];

  return <>
    <SiteHeader hideSignup />
    <main className="partner-page">
      <section className="partner-hero professional-landing-hero">
        <div className="professional-hero-copy">
          <p className="eyebrow"><span>For professionals</span> Calgary launch</p>
          <h1>More work that <em>fits.</em></h1>
          <p className="lead">Advoxy helps independent hair and nail professionals find thoughtful customers, manage their availability, and run every appointment from one calm mobile workspace.</p>
          <div className="mobile-only-note"><strong>Professional signup is mobile-only.</strong><span>Create your account and complete verification in the Advoxy professional app.</span></div>
        </div>
        <div className="app-download-card" id="download">
          <div className="phone-mockup" aria-hidden="true"><div className="phone-speaker" /><div className="phone-screen"><span className="phone-logo">advoxy</span><span className="phone-kicker">PROFESSIONAL</span><strong>Work on your terms.</strong><div className="phone-lines"><i /><i /><i /></div><span className="phone-tabbar">Home&nbsp;&nbsp; Bookings&nbsp;&nbsp; Profile</span></div></div>
          <div className="download-copy"><p className="eyebrow"><span>01</span> Start on mobile</p><h2>Download the app to sign up.</h2><p>Scan the code or use your phone to open the professional app. Website signup is not available for professionals.</p><div className="qr-code" aria-label="QR code placeholder for the Advoxy professional app">{qrPattern.map((row, rowIndex) => row.split("").map((cell, cellIndex) => <i className={cell === "1" ? "filled" : ""} key={`${rowIndex}-${cellIndex}`} />))}</div><span className="qr-caption">Scan to download</span></div>
        </div>
      </section>
      <section className="wrap section professional-process"><p className="eyebrow"><span>02 / 04</span> How Advoxy works</p><div className="section-head"><h2>Everything you need to <em>operate well.</em></h2><p>From your first profile edit to the final customer handoff, the app keeps the work clear.</p></div><div className="steps">{steps.map(([number, title, detail]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{detail}</p></article>)}</div></section>
      <section className="partner-band"><div className="wrap professional-band-content"><div><p className="eyebrow"><span>03 / 04</span> Built for independent work</p><h2>Clear pricing. Verified trust. <em>More control.</em></h2><p>Manage services, prices, service radius, availability, bookings, customer messages, and earnings from the professional app.</p></div><Link className="btn btn-outline-light" href="#download">Get the app</Link></div></section>
      <section className="wrap professional-faq"><p className="eyebrow"><span>04 / 04</span> Before you start</p><div className="faq-grid"><article><h3>Can I sign up on the website?</h3><p>No. Professional registration and verification are handled exclusively in the Advoxy mobile app.</p></article><article><h3>What happens after signup?</h3><p>Complete your profile, add services and availability, then submit your verification before accepting customer bookings.</p></article><article><h3>Do customers book through the app?</h3><p>Customers can discover and book through the Advoxy marketplace while you manage the work from your professional app.</p></article></div></section>
    </main>
  </>;
}
