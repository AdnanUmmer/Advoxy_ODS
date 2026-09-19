import Link from "next/link";
import { notFound } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import { getCategory } from "@/lib/api";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const category = await getCategory(slug);
    return { title: `${category.name} services | Advoxy`, description: `Book verified ${category.name.toLowerCase()} professionals in Calgary with Advoxy.` };
  } catch {
    return { title: "Services | Advoxy" };
  }
}

export default async function ServiceCategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let category;
  try { category = await getCategory(slug); } catch { notFound(); }
  if (!category) notFound();

  return (
    <>
      <SiteHeader />
      <div className="nav-spacer" />

      <main className="wrap">
        <div className="service-category-page">
          <p className="eyebrow">
            <span>Advoxy services</span> Calgary
          </p>
          <h1>
            {category.name} that feels <em>like you.</em>
          </h1>
          <p className="lead">
            Choose a service, then compare verified professionals, pricing, and open time.
          </p>

          {category.subcategories.length === 0 ? (
            <div className="empty-state">
              No {category.name.toLowerCase()} services are available right now.
            </div>
          ) : (
            <>
              <div className="subcategory-cards" aria-label={`${category.name} service groups`}>
                {category.subcategories.map((subcategory) => (
                  <a className="subcategory-card" href={`#subcategory-${subcategory.slug}`} key={subcategory.id}>
                    <span>{String(subcategory.services.length).padStart(2, "0")} services</span>
                    <h2>{subcategory.name}</h2>
                    <strong>Explore services <span aria-hidden="true">↘</span></strong>
                  </a>
                ))}
              </div>
              {category.subcategories.map((subcategory) => (
                <section key={subcategory.id} className="subcategory-section" id={`subcategory-${subcategory.slug}`}>
                  <div className="subcategory-heading"><p className="eyebrow">{category.name} services</p><h2 className="subcategory-title">{subcategory.name}</h2></div>
                <div className="service-grid">
                  {subcategory.services.map((service) => (
                    <Link
                      className="service-item"
                      href={`/search?service=${service.id}&service_name=${encodeURIComponent(service.name)}&q=${encodeURIComponent(service.name)}&booking_type=SCHEDULED`}
                      key={service.id}
                      style={{ textDecoration: "none", color: "inherit" }}
                    >
                      <div className="service-content">
                        <h3>{service.name}</h3>
                        <p>{service.description || `Find a verified professional for ${service.name.toLowerCase()}.`}</p>
                      </div>
                      <span className="service-arrow" aria-hidden="true">
                        →
                      </span>
                    </Link>
                  ))}
                </div>
                </section>
              ))}
            </>
          )}
        </div>
      </main>
    </>
  );
}
