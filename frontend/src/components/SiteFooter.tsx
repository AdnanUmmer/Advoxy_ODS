import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="wrap footer-grid">
        <div>
          <h2>Better appointments,<br />closer to home.</h2>
          <p>Made for Calgary, Alberta, with room to expand across Canada.</p>
        </div>
        <div>
          <h3>Explore</h3>
          <Link href="/services">Services</Link>
          <Link href="/book/instant">Available now</Link>
          <Link href="/signup">Create account</Link>
          <Link href="/dashboard">My bookings</Link>
        </div>
        <div>
          <h3>For professionals</h3>
          <Link href="/professionals">How it works</Link>
          <Link href="/professionals#download">Download the app</Link>
          <Link href="/professionals#download">Mobile signup</Link>
        </div>
        <div>
          <h3>Contact</h3>
          <a href="mailto:hello@advoxy.ca">hello@advoxy.ca</a>
          <a href="mailto:support@advoxy.ca">Customer support</a>
          <Link href="/privacy">Privacy</Link>
          <Link href="/terms">Terms</Link>
        </div>
      </div>
      <div className="wrap footer-bottom">
        <span>© 2026 Advoxy. All rights reserved.</span>
        <div className="social-links" aria-label="Social links">
          <a href="https://www.instagram.com" target="_blank" rel="noreferrer">Instagram</a>
          <a href="https://www.facebook.com" target="_blank" rel="noreferrer">Facebook</a>
          <a href="https://www.linkedin.com" target="_blank" rel="noreferrer">LinkedIn</a>
          <a href="https://x.com" target="_blank" rel="noreferrer">X</a>
        </div>
      </div>
    </footer>
  );
}
