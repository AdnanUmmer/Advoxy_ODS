"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { autocompleteLocation, getPlaceDetails, reverseGeocode } from "@/lib/api";
import DateTimePicker from "@/components/DateTimePicker";

type Suggestion = { id: number; name: string; category: string };

type HeroSearchProps = { suggestions: Suggestion[] };

const bookingOptions = [
  { label: "Instant", value: "instant" },
  { label: "Today", value: "today" },
  { label: "Tomorrow", value: "tomorrow" },
  { label: "Choose a date & time", value: "scheduled" },
];

export default function HeroSearch({ suggestions }: HeroSearchProps) {
  const router = useRouter();
  const [service, setService] = useState("");
  const [serviceId, setServiceId] = useState<number | null>(null);
  const [location, setLocation] = useState("Calgary");
  const [when, setWhen] = useState("instant");
  const [scheduledTime, setScheduledTime] = useState("");
  const [open, setOpen] = useState<"service" | "location" | "when" | null>(null);
  const [activeSuggestion, setActiveSuggestion] = useState(0);
  const [locationMessage, setLocationMessage] = useState("");
  const [coordinates, setCoordinates] = useState<{ latitude: number; longitude: number } | null>(null);
  const [serviceAreaMessage, setServiceAreaMessage] = useState("");
  const [locationPredictions, setLocationPredictions] = useState<{ place_id: string; description: string }[]>([]);

  const filteredSuggestions = useMemo(() => {
    const search = service.trim().toLowerCase();
    if (!search || search === "hair services") return suggestions.slice(0, 5);
    return suggestions.filter((item) => item.name.toLowerCase().includes(search)).slice(0, 5);
  }, [service, suggestions]);

  useEffect(() => {
    if (location.trim().length < 2 || open !== "location") {
      return;
    }
    const timer = window.setTimeout(() => {
      autocompleteLocation(location).then((result) => setLocationPredictions(result.predictions)).catch(() => setLocationPredictions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [location, open]);

  async function selectLocation(placeId: string) {
    try {
      const result = await getPlaceDetails(placeId);
      if (result.province && result.province !== "Alberta") {
        setLocation(result.city || result.formatted_address);
        setCoordinates(null);
        setLocationPredictions([]);
        setServiceAreaMessage("Coming soon in your location. Advoxy is currently available in Alberta.");
        setOpen(null);
        return;
      }
      setLocation(result.city || result.formatted_address);
      setCoordinates({ latitude: result.latitude, longitude: result.longitude });
      setLocationMessage("");
      setServiceAreaMessage("");
      setLocationPredictions([]);
      setOpen(null);
    } catch {
      setLocationMessage("That location could not be selected. Please try another result.");
    }
  }

  function handleServiceKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestion((current) => Math.min(current + 1, filteredSuggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestion((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && filteredSuggestions[activeSuggestion]) {
      event.preventDefault();
      setService(filteredSuggestions[activeSuggestion].name);
      setServiceId(filteredSuggestions[activeSuggestion].id);
      setOpen(null);
    } else if (event.key === "Escape") {
      setOpen(null);
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationMessage("Your browser does not provide location. Search by city instead.");
      return;
    }
    setLocationMessage("Requesting your location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        reverseGeocode(position.coords.latitude, position.coords.longitude).then((result) => {
          if (result.province && result.province !== "Alberta") {
            setCoordinates(null);
            setServiceAreaMessage("Coming soon in your location. Advoxy is currently available in Alberta.");
            setOpen(null);
            return;
          }
          setLocation(result.city || result.formatted_address || "Current location");
          setCoordinates({ latitude: position.coords.latitude, longitude: position.coords.longitude });
          setLocationMessage("Current location selected.");
          setOpen(null);
        }).catch(() => setLocationMessage("Location was found, but address lookup is unavailable. Enter a city manually."));
      },
      () => setLocationMessage("Location permission was denied. Enter a city manually."),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (serviceAreaMessage) {
      setLocationMessage(serviceAreaMessage);
      setOpen("location");
      return;
    }
    if (!serviceId) {
      setLocationMessage("Please select a service from the list.");
      setOpen("service");
      return;
    }
    if (!location.trim()) {
      setLocationMessage("Please enter a location or use your current location.");
      setOpen("location");
      return;
    }

    let bookingType = "SCHEDULED";
    let finalDate = scheduledTime.slice(0, 10);
    const finalTime = scheduledTime.slice(11, 16);

    if (when === "instant") {
      bookingType = "INSTANT";
    } else if (when === "today") {
      finalDate = new Date().toISOString().split("T")[0];
    } else if (when === "tomorrow") {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      finalDate = tomorrow.toISOString().split("T")[0];
    }

    if (bookingType === "SCHEDULED" && (!finalDate || !finalTime)) {
      setLocationMessage("Please choose a date and time.");
      setOpen("when");
      return;
    }

    const params = new URLSearchParams({ service: String(serviceId), service_name: service, location, when });
    if (bookingType === "SCHEDULED") {
      if (finalDate) params.set("date", finalDate);
      if (finalTime) params.set("time", finalTime);
    }
    params.set("booking_type", bookingType);
    if (coordinates) {
      params.set("latitude", String(coordinates.latitude));
      params.set("longitude", String(coordinates.longitude));
    }
    router.push(`/search?${params.toString()}`);
  }

  return (
    <form className="search-card" onSubmit={submit}>
      <div className="search-field-wrap">
        <label>
          <span>I&apos;m looking for</span>
          <input aria-autocomplete="list" aria-controls="service-suggestions" value={service} name="service" onChange={(event) => { setService(event.target.value); setServiceId(null); setOpen("service"); setActiveSuggestion(0); }} onFocus={() => setOpen("service")} onKeyDown={handleServiceKeyDown} />
        </label>
        {open === "service" && filteredSuggestions.length > 0 && <ul className="search-dropdown" id="service-suggestions" role="listbox">{filteredSuggestions.map((item, index) => <li key={`${item.category}-${item.name}`}><button type="button" role="option" aria-selected={index === activeSuggestion} onMouseDown={(event) => event.preventDefault()} onClick={() => { setService(item.name); setServiceId(item.id); setOpen(null); }}>{item.name}<small>{item.category}</small></button></li>)}</ul>}
      </div>
      <div className="search-field-wrap">
        <label>
          <span>Near</span>
          <input value={location} name="location" onChange={(event) => { setLocation(event.target.value); setLocationPredictions([]); }} onFocus={() => setOpen("location")} />
        </label>
        {open === "location" && <div className="search-dropdown location-dropdown"><button type="button" onClick={useCurrentLocation}>Use my current location</button>{locationPredictions.map((prediction) => <button type="button" key={prediction.place_id} onClick={() => void selectLocation(prediction.place_id)}>{prediction.description}</button>)}<p>{serviceAreaMessage || locationMessage || "Or enter a city, neighbourhood, or address."}</p></div>}
      </div>
      <div className="search-field-wrap">
        <label>
          <span>When</span>
          <div className="custom-select" onClick={() => setOpen(open === "when" ? null : "when")}>
            {bookingOptions.find((opt) => opt.value === when)?.label || "Select when"}
          </div>
        </label>
        {open === "when" && (
          <div className="search-dropdown when-dropdown">
            {bookingOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={when === option.value ? "active" : ""}
                onClick={() => {
                  setWhen(option.value);
                  setOpen(null);
                }}
              >
                {option.label}
              </button>
            ))}
            {when === "scheduled" && <DateTimePicker value={scheduledTime} onChange={(value) => setScheduledTime(value)} />}
          </div>
        )}
      </div>
      <button className="btn btn-primary" type="submit">Explore professionals</button>
    </form>
  );
}
