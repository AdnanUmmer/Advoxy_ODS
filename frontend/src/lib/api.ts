/**
 * Single fetch wrapper for the DRF backend. Every request goes through
 * here so auth headers, base URL, and error shape stay in one place —
 * same contract the Flutter app will hit, so web and mobile stay two
 * clients of one API rather than diverging.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
export const AUTH_BASE_URL = process.env.NEXT_PUBLIC_AUTH_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? window.localStorage.getItem("advoxy_token") : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export type Category = {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  subcategories: {
    id: number;
    name: string;
    slug: string;
    audience: "MEN" | "WOMEN" | "KIDS" | "UNISEX";
    display_order: number;
    services: {
      id: number;
      name: string;
      slug: string;
      description: string;
      is_active: boolean;
      duration_minutes: number;
      default_price: string;
      category_slug: string;
    }[];
  }[];
};

export type Professional = {
  id: number;
  display_name: string;
  area: string;
  bio: string;
  years_experience: number;
  is_online: boolean;
  is_active: boolean;
  average_rating: string | null;
  review_count: number;
  distance_km: number | null;
  services: {
    id: number;
    service_catalog_id: number;
    name: string;
    slug: string;
    category: string;
    category_slug: string;
    subcategory: string;
    subcategory_slug: string;
    audience: "MEN" | "WOMEN" | "KIDS" | "UNISEX";
    price: string;
    duration_minutes: number;
  }[];
};

export type Address = {
  id: number;
  label: string;
  full_address: string;
  latitude: string;
  longitude: string;
  is_default: boolean;
};

export type Booking = {
  id: number;
  professional: number | null;
  professional_service: number;
  address: number;
  booking_type: "INSTANT" | "SCHEDULED";
  status: string;
  service_price: string;
  duration_minutes: number;
  travel_fee: string;
  priority_fee: string;
  total_amount: string;
  scheduled_time: string | null;
  created_at: string;
  professional_name?: string | null;
  service_name?: string;
  service_category?: string;
  address_label?: string;
  address_full?: string;
  updated_at?: string;
  completed_at?: string | null;
  confirmed_complete_at?: string | null;
};

export type BookingNotification = { id: number; booking: number; event: string; body: string; read_at: string | null; created_at: string };
export type Conversation = { id: number; booking: number; created_at: string; messages: { id: number; sender: number; sender_name: string; body: string; read_at: string | null; created_at: string }[] };

export type AvailabilitySlot = {
  id: number;
  professional: number;
  start_time: string;
  end_time: string;
  is_booked: boolean;
};

export type ProfessionalService = {
  id: number;
  professional: number;
  professional_name: string;
  professional_rating: string | null;
  is_online: boolean;
  is_available_now: boolean;
  service_name: string;
  service_slug: string;
  category_name: string;
  category_slug: string;
  subcategory_name: string;
  subcategory_slug: string;
  audience: "MEN" | "WOMEN" | "KIDS" | "UNISEX";
  price: string;
  duration_minutes: number;
};

export type ManagedProfessionalService = {
  id: number;
  service: number;
  price: string;
  duration_minutes: number;
  is_active: boolean;
};

export type AdminDashboard = {
  counts: Record<string, number>;
  recent_bookings: Booking[];
  popular_services: { service__name: string; total: number }[];
};

type ListResponse<T> = T[] | { results: T[] };

function unwrapList<T>(response: ListResponse<T>) {
  return Array.isArray(response) ? response : response.results;
}

export async function getCategories() {
  const response = await apiFetch<ListResponse<Category>>("/categories/", {
    cache: "no-store",
  });
  return unwrapList(response);
}

export async function getCategory(slug: string) {
  return apiFetch<Category>(`/categories/${encodeURIComponent(slug)}/`, { cache: "no-store" });
}

export async function getProfessionals(options: { availableNow?: boolean; query?: string; city?: string; service?: string; serviceSlug?: string; category?: string; audience?: string; bookingType?: string; latitude?: number; longitude?: number; scheduledTime?: string; minRating?: number; minPrice?: number; maxPrice?: number; ordering?: string } = {}) {
  const params = new URLSearchParams();
  if (options.availableNow) params.set("available_now", "1");
  if (options.query) params.set("q", options.query);
  if (options.city) params.set("city", options.city);
  if (options.service) params.set("service", options.service);
  if (options.serviceSlug) params.set("service_slug", options.serviceSlug);
  if (options.category) params.set("category", options.category);
  if (options.audience) params.set("audience", options.audience);
  if (options.bookingType) params.set("booking_type", options.bookingType);
  if (options.latitude !== undefined) params.set("latitude", String(options.latitude));
  if (options.longitude !== undefined) params.set("longitude", String(options.longitude));
  if (options.scheduledTime) params.set("scheduled_time", options.scheduledTime);
  if (options.minRating !== undefined) params.set("min_rating", String(options.minRating));
  if (options.minPrice !== undefined) params.set("min_price", String(options.minPrice));
  if (options.maxPrice !== undefined) params.set("max_price", String(options.maxPrice));
  if (options.ordering) params.set("ordering", options.ordering);
  const response = await apiFetch<ListResponse<Professional>>(
    `/professionals/${params.size ? `?${params.toString()}` : ""}`,
    { cache: "no-store" }
  );
  return unwrapList(response);
}

export type MarketplaceSettings = Record<string, string | number | boolean>;

export async function getMarketplaceSettings() {
  return apiFetch<MarketplaceSettings>("/admin/settings/");
}

export async function updateMarketplaceSettings(payload: MarketplaceSettings & { reason?: string }) {
  return apiFetch<MarketplaceSettings>("/admin/settings/", { method: "PATCH", body: JSON.stringify(payload) });
}

export type AdminCatalog = {
  services: { id: number; name: string; duration_minutes: number }[];
  professional_services: { id: number; professional_id: number; professional_name: string; service_id: number; service_name: string; price: string; duration_minutes: number }[];
};

export async function getAdminCatalog() {
  return apiFetch<AdminCatalog>("/admin/catalog/");
}

export async function updateAdminCatalog(payload: { service_id?: number; duration_minutes?: number; professional_service_id?: number; price?: number }) {
  return apiFetch<{ id: number; duration_minutes?: number; price?: string }>("/admin/catalog/", { method: "PATCH", body: JSON.stringify(payload) });
}

export async function getProfessional(id: number) {
  return apiFetch<Professional>(`/professionals/${id}/`, { cache: "no-store" });
}

export async function reverseGeocode(latitude: number, longitude: number) {
  return apiFetch<{ formatted_address: string; city: string; province?: string }>(`/location/reverse/?latitude=${latitude}&longitude=${longitude}`);
}

export async function autocompleteLocation(input: string) {
  return apiFetch<{ predictions: { place_id: string; description: string }[] }>(`/location/autocomplete/?input=${encodeURIComponent(input)}`);
}

export async function getPlaceDetails(placeId: string) {
  return apiFetch<{ formatted_address: string; city: string; province?: string; latitude: number; longitude: number; place_id: string }>(`/location/details/?place_id=${encodeURIComponent(placeId)}`);
}

export async function geocodeAddress(address: string) {
  return apiFetch<{ formatted_address: string; city: string; latitude: number; longitude: number }>(`/location/geocode/?address=${encodeURIComponent(address)}`);
}

export async function requestPasswordReset(email: string) {
  return apiFetch<{ detail: string }>("/auth/password-reset/", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(payload: { uid: number; token: string; new_password: string }) {
  return apiFetch<{ detail: string }>("/auth/password-reset/confirm/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAddresses() {
  const response = await apiFetch<ListResponse<Address>>("/addresses/");
  return unwrapList(response);
}

export async function getProfessionalServices() {
  const response = await apiFetch<ListResponse<ProfessionalService>>(
    "/professional-services/"
  );
  return unwrapList(response);
}

export async function getAvailability(professional?: number) {
  const response = await apiFetch<ListResponse<AvailabilitySlot>>(`/availability/${professional ? `?professional=${professional}` : ""}`);
  return unwrapList(response);
}

export async function getCatalogServices(category?: string) {
  const response = await apiFetch<ListResponse<{ id: number; name: string; description: string; is_active: boolean }>>(`/services/${category ? `?category=${encodeURIComponent(category)}` : ""}`);
  return unwrapList(response);
}

export async function getManagedProfessionalServices() {
  const response = await apiFetch<ListResponse<ManagedProfessionalService>>("/professional/manage-services/");
  return unwrapList(response);
}

export async function createManagedProfessionalService(payload: { service: number; price: string; duration_minutes: number; is_active: boolean }) {
  return apiFetch<ManagedProfessionalService>("/professional/manage-services/", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateProfessionalProfile(payload: { bio?: string; service_radius_km?: string; service_cities?: string[] }) {
  return apiFetch<Professional>("/professional/profile/", { method: "PATCH", body: JSON.stringify(payload) });
}

export async function createAddress(payload: Omit<Address, "id">) {
  return apiFetch<Address>("/addresses/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createBooking(payload: {
  professional_service: number;
  address: number;
  booking_type: "INSTANT" | "SCHEDULED";
  scheduled_time?: string;
  availability_slot?: number;
}) {
  return apiFetch<Booking>("/bookings/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createPaymentIntent(booking: number) {
  return apiFetch<{ payment_intent_id: string; client_secret: string; status: string }>("/payments/intent/", {
    method: "POST",
    body: JSON.stringify({ booking }),
  });
}

export async function confirmPaymentIntent(payment_intent_id: string) {
  return apiFetch<{ payment_intent_id: string; status: string }>("/payments/confirm/", {
    method: "POST",
    body: JSON.stringify({ payment_intent_id }),
  });
}

export async function getBookings() {
  const response = await apiFetch<ListResponse<Booking>>("/bookings/");
  return unwrapList(response);
}

export async function getBooking(id: number) {
  return apiFetch<Booking>(`/bookings/${id}/`);
}

export async function getFavorites() {
  return apiFetch<Professional[]>("/favorites/");
}

export async function setFavorite(professionalId: number, favorite: boolean) {
  return apiFetch<{ professional: number; favorite: boolean }>(`/favorites/${professionalId}/`, { method: favorite ? "POST" : "DELETE", body: JSON.stringify({}) });
}

export async function getNotifications() {
  const response = await apiFetch<ListResponse<BookingNotification>>("/notifications/");
  return unwrapList(response);
}

export async function getConversations() {
  const response = await apiFetch<ListResponse<Conversation>>("/conversations/");
  return unwrapList(response);
}

export async function sendConversationMessage(id: number, body: string) {
  return apiFetch<Conversation["messages"][number]>(`/conversations/${id}/send/`, { method: "POST", body: JSON.stringify({ body }) });
}

export async function markConversationRead(id: number) {
  return apiFetch<{ read: boolean }>(`/conversations/${id}/read/`, { method: "POST", body: JSON.stringify({}) });
}

export async function getMe() {
  return apiFetch<{ id: number; email: string; first_name: string; last_name: string; role: string }>("/auth/me/");
}

export async function cancelBooking(id: number) {
  return apiFetch<Booking>(`/bookings/${id}/cancel/`, { method: "POST", body: JSON.stringify({}) });
}

export async function login(payload: { username: string; password: string }) {
  const response = await apiFetch<{ token: string; id: number; email: string; first_name: string; last_name: string; role: string }>(
    "/auth/login/",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  localStorage.setItem("advoxy_token", response.token);
  return response;
}

export async function googleLogin(payload: { credential: string; role?: "CUSTOMER" | "PROFESSIONAL" }) {
  const response = await apiFetch<{ token: string; id: number; email: string; first_name: string; last_name: string; role: string }>(
    "/auth/google/",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
  localStorage.setItem("advoxy_token", response.token);
  return response;
}

export async function signup(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  date_of_birth: string;
  role: string;
}) {
  const response = await apiFetch<{ id: number; token: string }>(
    "/auth/register/",
    {
      method: "POST",
      body: JSON.stringify({
        username: payload.email,
        ...payload,
      }),
    }
  );
  localStorage.setItem("advoxy_token", response.token);
  return response;
}

export async function logout() {
  await apiFetch<void>("/auth/logout/", { method: "POST", body: JSON.stringify({}) });
  localStorage.removeItem("advoxy_token");
}

export async function getAdminDashboard() {
  return apiFetch<AdminDashboard>("/admin/dashboard/");
}

export async function getProfessionalDashboard() {
  return apiFetch<{ profile: Professional; bookings: Booking[] }>("/professional/dashboard/");
}

export async function updateProfessionalStatus(is_online: boolean) {
  return apiFetch<{ is_online: boolean }>("/professional/status/", {
    method: "POST",
    body: JSON.stringify({ is_online }),
  });
}

export async function bookingAction(id: number, action: string, payload: Record<string, unknown> = {}) {
  return apiFetch<Booking>(`/bookings/${id}/${action}/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getReviews(professionalId: number) {
  const response = await apiFetch<ListResponse<{ id: number; rating: number; comment: string; customer_name: string; created_at: string }>>(
    `/reviews/?professional=${professionalId}`,
    { cache: "no-store" }
  );
  return unwrapList(response);
}

export async function createReview(payload: { booking: number; rating: number; comment: string }) {
  return apiFetch<{ id: number }>("/reviews/", { method: "POST", body: JSON.stringify(payload) });
}
