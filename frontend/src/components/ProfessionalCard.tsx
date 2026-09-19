"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { setFavorite } from "@/lib/api";

export type ProfessionalCardProps = {
  professional: {
    id: number;
    display_name: string;
    area: string;
    years_experience: number;
    is_online: boolean;
    average_rating: string | null;
    review_count: number;
    distance_km: number | null;
    services: {
      id: number;
      name: string;
      price: string;
    }[];
  };
  gradient?: string;
  isFavorite?: boolean;
};

export default function ProfessionalCard({ professional, gradient, isFavorite = false }: ProfessionalCardProps) {
  const searchParams = useSearchParams();
  const [favorite, setFavoriteState] = useState(isFavorite);
  const [favoriteBusy, setFavoriteBusy] = useState(false);
  const initials = (name: string) =>
    name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();

  const defaultGradients = [
    "from-[#7a4a6b] to-[#2c1a28]",
    "from-[#4a5a7a] to-[#1a212c]",
    "from-[#5a7a4a] to-[#212c1a]",
    "from-[#7a5a4a] to-[#2c1e1a]",
  ];

  const activeGradient = gradient || defaultGradients[professional.id % defaultGradients.length];
  const profileHref = `/professionals/${professional.id}${searchParams.size ? `?${searchParams.toString()}` : ""}`;

  async function toggleFavorite(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (favoriteBusy || !localStorage.getItem("advoxy_token")) return;
    setFavoriteBusy(true);
    try {
      const result = await setFavorite(professional.id, !favorite);
      setFavoriteState(result.favorite);
    } finally {
      setFavoriteBusy(false);
    }
  }

  return (
    <Link
      className="result-card"
      href={profileHref}
      style={{ textDecoration: "none", color: "inherit" }}
    >
      <div className={`result-photo bg-linear-to-br ${activeGradient}`}>
        <span className="badge-verified">Verified</span>
        {professional.is_online && (
          <span className="badge-online">
            <span className="dot"></span>Online now
          </span>
        )}
        <button className={`favorite-button ${favorite ? "active" : ""}`} type="button" aria-label={favorite ? "Remove from favorites" : "Add to favorites"} onClick={toggleFavorite} disabled={favoriteBusy}>{favorite ? "♥" : "♡"}</button>
        <span className="initials">{initials(professional.display_name)}</span>
      </div>
      <div>
        <div className="result-name">{professional.display_name}</div>
        <div className="result-role">
          {professional.services[0]?.name ?? "Beauty professional"} · {professional.area || "Calgary"} · {professional.years_experience} yrs experience
        </div>
        <div className="result-meta">
          <span className="rating">★ {professional.average_rating ?? "New"}</span>
          <span>{professional.review_count} reviews</span>
          <span>{professional.distance_km === null ? "Distance unavailable" : `${professional.distance_km.toFixed(1)} km away`}</span>
        </div>
        <div className="result-tags">
          {professional.services.slice(0, 3).map((service) => (
            <span key={service.id}>{service.name}</span>
          ))}
        </div>
      </div>
      <div className="result-cta">
        <div className="price">
          From ${Number.parseFloat(professional.services[0]?.price ?? "75").toFixed(0)}
          <small> CAD</small>
        </div>
        <div className="next-slot">
          Next slot: {professional.is_online ? "Today, 14:30" : "Tomorrow, 10:00"}
        </div>
        <span className="btn btn-outline small">Book</span>
      </div>
    </Link>
  );
}
