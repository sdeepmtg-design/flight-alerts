import Constants from "expo-constants";
import * as SecureStore from "expo-secure-store";

const DEVICE_KEY = "flight_alerts_device_id";

export type Route = {
  id: number;
  destination_iata: string;
  destination_country: string | null;
  destination_city: string | null;
  max_price: number;
  label: string | null;
  trip_class: number;
  departure_month: string | null;
  departure_date: string | null;
  date_flex_days: number;
  one_way: boolean;
  last_price: number | null;
  last_departure: string | null;
  last_return: string | null;
  last_checked: string | null;
};

export type RouteCreate = {
  destination_iata: string;
  destination_country?: string;
  destination_city?: string;
  max_price: number;
  label?: string;
  trip_class?: number;
  departure_month?: string | null;
  departure_date?: string | null;
  date_flex_days?: number;
  one_way?: boolean;
};

export type Me = {
  device_id: string;
  origin_iata: string | null;
  routes_count: number;
};

function apiBase(): string {
  const extra = Constants.expoConfig?.extra as { apiUrl?: string } | undefined;
  return extra?.apiUrl ?? "http://localhost:8000";
}

async function deviceId(): Promise<string> {
  let id = await SecureStore.getItemAsync(DEVICE_KEY);
  if (!id) {
    id = `dev_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
    await SecureStore.setItemAsync(DEVICE_KEY, id);
  }
  return id;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const id = await deviceId();
  const res = await fetch(`${apiBase()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Device-Id": id,
      ...(options.headers as Record<string, string>),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  getMe: () => request<Me>("/me"),
  updateMe: (body: { origin_iata?: string; push_token?: string }) =>
    request<Me>("/me", { method: "PATCH", body: JSON.stringify(body) }),
  listRoutes: () => request<Route[]>("/routes"),
  addRoute: (body: RouteCreate) =>
    request<Route>("/routes", { method: "POST", body: JSON.stringify(body) }),
  deleteRoute: (id: number) =>
    request<void>(`/routes/${id}`, { method: "DELETE" }),
};
