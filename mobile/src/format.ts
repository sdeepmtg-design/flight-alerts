export function formatFlightDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const yyyy = d.getFullYear();
    return `${dd}.${mm}.${yyyy}`;
  } catch {
    return iso.slice(0, 10);
  }
}

export function describeDateFilter(route: {
  departure_month?: string | null;
  departure_date?: string | null;
  date_flex_days?: number;
}): string {
  if (route.departure_date) {
    const base = formatFlightDate(route.departure_date) ?? route.departure_date;
    if ((route.date_flex_days ?? 0) >= 3) return `±3 дня от ${base}`;
    return `дата ${base}`;
  }
  if (route.departure_month) {
    const [y, m] = route.departure_month.split("-");
    const names = [
      "", "янв", "фев", "мар", "апр", "май", "июн",
      "июл", "авг", "сен", "окт", "ноя", "дек",
    ];
    return `только ${names[Number(m)]} ${y}`;
  }
  return "ближайшие 4 мес.";
}

const TRIP_CLASS_LABELS: Record<number, string> = {
  0: "эконом",
  1: "бизнес",
  2: "первый",
};

export function describeTripClass(tripClass: number | null | undefined): string {
  return TRIP_CLASS_LABELS[tripClass ?? 0] ?? "эконом";
}
