import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import { getCategories } from "@/lib/api";

export const metadata = {
  title: "Services | Advoxy",
  description: "Browse Advoxy hair and nail services.",
};

export default async function ServicesPage() {
  const categories = await getCategories().catch(() => []);

  return (
    <>
      <SiteHeader />
      <div className="nav-spacer" />
      <main className="wrap section">
        <p className="eyebrow">Services</p>
        <h1>Choose your ritual.</h1>
        <div className="cat-grid">
          {categories.length === 0 ? (
            <div className="empty-state">Service categories are unavailable right now.</div>
          ) : (
            categories.map((category) => (
              <Link
                key={category.id}
                className={`cat-card ${category.slug === "nails" ? "nails" : "hair"}`}
                href={`/services/${category.slug}`}
              >
                <span>{category.subcategories[0]?.name ?? "Services"}</span>
                <h3>{category.name}</h3>
              </Link>
            ))
          )}
        </div>
      </main>
    </>
  );
}
