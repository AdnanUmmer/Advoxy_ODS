"use client";

import { FormEvent, useEffect, useState } from "react";
import { createManagedProfessionalService, getCatalogServices, getManagedProfessionalServices, ManagedProfessionalService } from "@/lib/api";

type CatalogService = { id: number; name: string; description: string; is_active: boolean };

export default function ProfessionalServicesPanel() {
  const [catalog, setCatalog] = useState<CatalogService[]>([]);
  const [services, setServices] = useState<ManagedProfessionalService[]>([]);
  const [service, setService] = useState("");
  const [price, setPrice] = useState("");
  const [duration, setDuration] = useState("60");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([getCatalogServices(), getManagedProfessionalServices()]).then(([nextCatalog, nextServices]) => {
      setCatalog(nextCatalog);
      setServices(nextServices);
      setService(String(nextCatalog[0]?.id ?? ""));
    }).catch(() => setMessage("Service settings could not be loaded."));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const created = await createManagedProfessionalService({ service: Number(service), price, duration_minutes: Number(duration), is_active: true });
      setServices((current) => [...current, created]);
      setMessage("Service added to your profile.");
      setPrice("");
    } catch {
      setMessage("That service could not be added. Check that it is not already configured.");
    }
  }

  return <section className="dashboard-section service-settings"><p className="eyebrow">Your offering</p><h2>Services and pricing</h2><form className="service-add-form" onSubmit={submit}><label className="field"><span>Catalog service</span><select value={service} onChange={(event) => setService(event.target.value)} required>{catalog.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field"><span>Price (CAD)</span><input value={price} onChange={(event) => setPrice(event.target.value)} type="number" min="1" step="0.01" required /></label><label className="field"><span>Duration (minutes)</span><input value={duration} onChange={(event) => setDuration(event.target.value)} type="number" min="15" max="480" required /></label><button className="btn btn-primary" type="submit">Add service</button></form>{services.length === 0 ? <div className="empty-state">No services configured yet.</div> : <div className="booking-list">{services.map((item) => <div className="booking-row" key={item.id}><div><span className="booking-id">Catalog service #{item.service}</span><h3>{catalog.find((entry) => entry.id === item.service)?.name ?? "Configured service"}</h3><p>{item.duration_minutes} minutes · ${Number.parseFloat(item.price).toFixed(2)} CAD</p></div><span className={`status-pill ${item.is_active ? "confirmed" : "cancelled_customer"}`}>{item.is_active ? "Active" : "Inactive"}</span></div>)}</div>}{message && <p className="form-message error">{message}</p>}</section>;
}