"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, getCategories, getFavorites, getProfessionals, Professional } from "@/lib/api";
import ProfessionalCard from "@/components/ProfessionalCard";
import SiteHeader from "@/components/SiteHeader";
import HeroSearch from "../HeroSearch";

export default function SearchPage() {
  const [query, setQuery] = useState(() => typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("professional") ?? "");
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [favoriteIds, setFavoriteIds] = useState<number[]>([]);
  const [serviceSuggestions, setServiceSuggestions] = useState<{ id: number; name: string; category: string }[]>([]);
  const [filters] = useState(() => {
    if (typeof window === "undefined") return { city: "", service: "", bookingType: "", latitude: "", longitude: "", scheduledTime: "" };
    const params = new URLSearchParams(window.location.search);
    return { city: params.get("location") ?? "", service: params.get("service") ?? "", bookingType: params.get("booking_type") ?? "", latitude: params.get("latitude") ?? "", longitude: params.get("longitude") ?? "", scheduledTime: params.get("date") && params.get("time") ? `${params.get("date")}T${params.get("time")}:00` : "" };
  });
  const [sort, setSort] = useState("recommended");
  const [minRating, setMinRating] = useState(4.5);
  const [maxPrice, setMaxPrice] = useState(300);
  const [availabilityToday, setAvailabilityToday] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");
  const uniqueProfessionals = Array.from(new Map(professionals.map((professional) => [professional.id, professional])).values());

  const searchOptions = useCallback((nextQuery = query) => {
    return { query: nextQuery, city: filters.city, service: filters.service, category: categoryFilter || undefined, bookingType: filters.bookingType, availableNow: filters.bookingType === "INSTANT" || availabilityToday, latitude: filters.latitude ? Number(filters.latitude) : undefined, longitude: filters.longitude ? Number(filters.longitude) : undefined, scheduledTime: filters.scheduledTime || undefined, minRating, maxPrice: maxPrice < 300 ? maxPrice : undefined, ordering: sort === "recommended" ? undefined : sort === "rating" ? "-rating" : sort === "experience" ? "-experience" : sort === "price" ? "price" : undefined };
  }, [availabilityToday, categoryFilter, filters, maxPrice, minRating, query, sort]);

  useEffect(() => {
    getCategories().then((categories) => setServiceSuggestions(categories.flatMap((category) => category.subcategories.flatMap((subcategory) => subcategory.services.map((service) => ({ id: service.id, name: service.name, category: category.name })))))).catch(() => undefined);
    if (localStorage.getItem("advoxy_token")) getFavorites().then((favorites) => setFavoriteIds(favorites.map((favorite) => favorite.id))).catch(() => undefined);
    const initial = new URLSearchParams(window.location.search).get("professional") ?? "";
    const params = new URLSearchParams(window.location.search);
    getProfessionals(searchOptions(params.get("q") ?? initial)).then((results) => {
      setProfessionals(results);
      setState("ready");
    }).catch(() => {
      setState("error");
      setMessage("Could not reach the marketplace API.");
    });
  }, [filters, minRating, maxPrice, availabilityToday, categoryFilter, sort, searchOptions]);

  async function search(nextQuery = query) {
    setState("loading");
    setMessage("");
    try {
      setProfessionals(await getProfessionals(searchOptions(nextQuery)));
      setState("ready");
    } catch (error) {
      setState("error");
      setMessage(error instanceof ApiError ? "Search is temporarily unavailable." : "Could not reach the marketplace API.");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void search();
  }

  return (
    <>
      <SiteHeader />
      <div className="nav-spacer" />

      <main className="wrap">
        <HeroSearch suggestions={serviceSuggestions} />
        <form className="search-bar legacy-search-bar" onSubmit={submit}>
          <div className="chip">
              <label>I&apos;m looking for</label>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Hair services"
            />
          </div>
          <div className="chip">
            <label>Near</label>
            <input
              value={filters.city}
              readOnly
              placeholder="Beltline, Calgary"
            />
          </div>
          <div className="chip">
            <label>When</label>
            <input
              value={filters.bookingType === "INSTANT" ? "Today" : "Any time"}
              readOnly
              placeholder="Any time"
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={state === "loading"}>
            {state === "loading" ? "Searching..." : "Search"}
          </button>
        </form>

        <div className="results-head">
              <span>{state === "ready" ? `${uniqueProfessionals.length} professionals near ${filters.city || "Calgary"}` : "Searching..."}</span>
          <div className="sort">
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="recommended">Sort: Recommended</option>
              <option value="rating">Highest rated</option>
              <option value="price">Price: low to high</option>
              <option value="experience">Most experienced</option>
            </select>
          </div>
        </div>

        <div className="layout">
          <aside className="filters">
            <div className="filters-heading"><strong>Refine results</strong><span>Compare your options</span></div>
            <div className="filter-group">
              <h4>Service</h4>
              <div className="filter-row"><input type="radio" name="category" checked={categoryFilter === ""} onChange={() => setCategoryFilter("")} /> All services</div>
              <div className="filter-row"><input type="radio" name="category" checked={categoryFilter === "hair"} onChange={() => setCategoryFilter("hair")} /> Hair</div>
              <div className="filter-row"><input type="radio" name="category" checked={categoryFilter === "nails"} onChange={() => setCategoryFilter("nails")} /> Nails</div>
            </div>
            <div className="filter-group">
              <h4>Price range</h4>
              <div className="price-range">
                <span>$40</span>
                <input type="range" min="40" max="300" value={maxPrice} onChange={(event) => setMaxPrice(Number(event.target.value))} />
                <span>${maxPrice >= 300 ? "300+" : maxPrice}</span>
              </div>
            </div>
            <div className="filter-group">
              <h4>Rating</h4>
              <div className="filter-row">
                <input type="radio" name="rating" checked={minRating === 4.9} onChange={() => setMinRating(4.9)} /> 4.9 &amp; up
              </div>
              <div className="filter-row">
                <input type="radio" name="rating" checked={minRating === 4.5} onChange={() => setMinRating(4.5)} /> 4.5 &amp; up
              </div>
              <div className="filter-row">
                <input type="radio" name="rating" checked={minRating === 0} onChange={() => setMinRating(0)} /> Any rating
              </div>
            </div>
            <div className="filter-group">
              <h4>Availability</h4>
              <div className="filter-row">
                <input type="checkbox" checked={availabilityToday} onChange={(event) => setAvailabilityToday(event.target.checked)} /> Available today
              </div>
              <div className="filter-row">
                <input type="checkbox" readOnly /> Available this week
              </div>
            </div>
            <div className="filter-group">
              <h4>Distance</h4>
              <div className="filter-row">
                <input type="radio" name="dist" readOnly /> Within 1 km
              </div>
              <div className="filter-row">
                <input type="radio" name="dist" checked readOnly /> Within 5 km
              </div>
              <div className="filter-row">
                <input type="radio" name="dist" readOnly /> Within 15 km
              </div>
            </div>
            <button className="clear-filters" type="button" onClick={() => { setCategoryFilter(""); setMinRating(0); setMaxPrice(300); setAvailabilityToday(false); setSort("recommended"); }}>Clear all filters</button>
          </aside>

          <div className="result-list" aria-live="polite">
            {state === "error" ? (
              <div className="empty-state error-state">{message}</div>
            ) : state === "loading" ? (
              <div className="empty-state">Loading verified professionals...</div>
            ) : state === "ready" && professionals.length === 0 ? (
              <div className="empty-state no-results-panel">
                <h2>No matching professionals right now</h2>
                <p>No verified professionals match that service, location, and time. Try instant availability or broaden the service search.</p>
                <div className="empty-actions">
                  <Link className="btn btn-primary small" href="/book/instant">See available now</Link>
                  <Link className="btn btn-outline small" href="/services">Choose another service</Link>
                </div>
              </div>
            ) : (
                uniqueProfessionals.map((professional) => (
                <ProfessionalCard key={professional.id} professional={professional} isFavorite={favoriteIds.includes(professional.id)} />
              ))
            )}
          </div>
        </div>
      </main>
    </>
  );
}
