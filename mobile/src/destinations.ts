export type City = { iata: string; name: string };
export type Country = { id: string; name: string; cities: City[] };

export const DEPARTURE_CITIES: City[] = [
  // Россия — крупнейшие хабы
  { iata: "MOW", name: "Москва" },
  { iata: "LED", name: "Санкт-Петербург" },
  { iata: "SVX", name: "Екатеринбург" },
  { iata: "KZN", name: "Казань" },
  { iata: "OVB", name: "Новосибирск" },
  { iata: "AER", name: "Сочи" },
  { iata: "KRR", name: "Краснодар" },
  { iata: "ROV", name: "Ростов-на-Дону" },
  { iata: "UFA", name: "Уфа" },
  { iata: "KUF", name: "Самара" },
  { iata: "GOJ", name: "Нижний Новгород" },
  { iata: "CEK", name: "Челябинск" },
  { iata: "KJA", name: "Красноярск" },
  { iata: "IKT", name: "Иркутск" },
  { iata: "MRV", name: "Минеральные Воды" },
  { iata: "VOZ", name: "Воронеж" },
  { iata: "ARH", name: "Архангельск" },
  { iata: "MMK", name: "Мурманск" },
  { iata: "VVO", name: "Владивосток" },
  { iata: "KHV", name: "Хабаровск" },
  { iata: "YKS", name: "Якутск" },
  // СНГ
  { iata: "MSQ", name: "Минск" },
  { iata: "ALA", name: "Алматы" },
  { iata: "NQZ", name: "Астана" },
  { iata: "TAS", name: "Ташкент" },
  { iata: "FRU", name: "Бишкек" },
  { iata: "EVN", name: "Ереван" },
  { iata: "TBS", name: "Тбилиси" },
  { iata: "BAK", name: "Баку" },
];

export const COUNTRIES: Country[] = [
  {
    id: "tr",
    name: "Турция",
    cities: [
      { iata: "IST", name: "Стамбул" },
      { iata: "AYT", name: "Анталья" },
      { iata: "ADB", name: "Измир" },
      { iata: "BJV", name: "Бодрум" },
    ],
  },
  {
    id: "ae",
    name: "ОАЭ",
    cities: [
      { iata: "DXB", name: "Дубай" },
      { iata: "AUH", name: "Абу-Даби" },
      { iata: "SHJ", name: "Шарджа" },
    ],
  },
  {
    id: "th",
    name: "Таиланд",
    cities: [
      { iata: "BKK", name: "Бангкок" },
      { iata: "HKT", name: "Пхукет" },
    ],
  },
  {
    id: "eg",
    name: "Египет",
    cities: [
      { iata: "HRG", name: "Хургада" },
      { iata: "SSH", name: "Шарм-эль-Шейх" },
      { iata: "CAI", name: "Каир" },
    ],
  },
  {
    id: "ge",
    name: "Грузия",
    cities: [
      { iata: "TBS", name: "Тбилиси" },
      { iata: "BUS", name: "Батуми" },
    ],
  },
  {
    id: "am",
    name: "Армения",
    cities: [{ iata: "EVN", name: "Ереван" }],
  },
  {
    id: "az",
    name: "Азербайджан",
    cities: [{ iata: "BAK", name: "Баку" }],
  },
  {
    id: "il",
    name: "Израиль",
    cities: [
      { iata: "TLV", name: "Тель-Авив" },
      { iata: "ETH", name: "Эйлат" },
    ],
  },
  {
    id: "cn",
    name: "Китай",
    cities: [
      { iata: "PEK", name: "Пекин" },
      { iata: "PVG", name: "Шанхай" },
    ],
  },
  {
    id: "vn",
    name: "Вьетнам",
    cities: [
      { iata: "SGN", name: "Хошимин" },
      { iata: "HAN", name: "Ханой" },
      { iata: "DAD", name: "Дананг" },
    ],
  },
  {
    id: "it",
    name: "Италия",
    cities: [
      { iata: "ROM", name: "Рим" },
      { iata: "MIL", name: "Милан" },
    ],
  },
  {
    id: "es",
    name: "Испания",
    cities: [
      { iata: "BCN", name: "Барселона" },
      { iata: "MAD", name: "Мадрид" },
    ],
  },
  {
    id: "fr",
    name: "Франция",
    cities: [{ iata: "PAR", name: "Париж" }],
  },
  {
    id: "de",
    name: "Германия",
    cities: [
      { iata: "BER", name: "Берлин" },
      { iata: "MUC", name: "Мюнхен" },
    ],
  },
  {
    id: "rs",
    name: "Сербия",
    cities: [{ iata: "BEG", name: "Белград" }],
  },
  {
    id: "me",
    name: "Черногория",
    cities: [
      { iata: "TIV", name: "Тиват" },
      { iata: "TGD", name: "Подгорица" },
    ],
  },
  {
    id: "gr",
    name: "Греция",
    cities: [
      { iata: "ATH", name: "Афины" },
      { iata: "HER", name: "Ираклион (Крит)" },
    ],
  },
  {
    id: "cy",
    name: "Кипр",
    cities: [
      { iata: "LCA", name: "Ларнака" },
      { iata: "PFO", name: "Пафос" },
    ],
  },
  {
    id: "qa",
    name: "Катар",
    cities: [{ iata: "DOH", name: "Доха" }],
  },
  {
    id: "jo",
    name: "Иордания",
    cities: [{ iata: "AMM", name: "Амман" }],
  },
  {
    id: "mv",
    name: "Мальдивы",
    cities: [{ iata: "MLE", name: "Мале" }],
  },
  {
    id: "lk",
    name: "Шри-Ланка",
    cities: [{ iata: "CMB", name: "Коломбо" }],
  },
  {
    id: "in",
    name: "Индия",
    cities: [
      { iata: "DEL", name: "Дели" },
      { iata: "GOI", name: "Гоа" },
    ],
  },
  {
    id: "id",
    name: "Индонезия",
    cities: [
      { iata: "DPS", name: "Бали" },
      { iata: "CGK", name: "Джakarta" },
    ],
  },
  {
    id: "my",
    name: "Малайзия",
    cities: [{ iata: "KUL", name: "Кuala Lumpur" }],
  },
  {
    id: "cz",
    name: "Чехия",
    cities: [{ iata: "PRG", name: "Прага" }],
  },
  {
    id: "at",
    name: "Австрия",
    cities: [{ iata: "VIE", name: "Вена" }],
  },
  {
    id: "nl",
    name: "Нидерланды",
    cities: [{ iata: "AMS", name: "Амsterdam" }],
  },
  {
    id: "pt",
    name: "Португалия",
    cities: [{ iata: "LIS", name: "Лиссabon" }],
  },
  {
    id: "us",
    name: "США",
    cities: [
      { iata: "NYC", name: "Нью-Йорк" },
      { iata: "MIA", name: "Майами" },
    ],
  },
];

export type DestinationOption = {
  country: Country;
  city: City;
  label: string;
};

export function searchDepartureCities(query: string): City[] {
  const q = query.trim().toLowerCase();
  if (!q) return DEPARTURE_CITIES;
  return DEPARTURE_CITIES.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.iata.toLowerCase().includes(q),
  );
}

export function searchDestinations(query: string): DestinationOption[] {
  const q = query.trim().toLowerCase();
  const out: DestinationOption[] = [];
  for (const country of COUNTRIES) {
    for (const city of country.cities) {
      const hay = `${country.name} ${city.name} ${city.iata}`.toLowerCase();
      if (!q || hay.includes(q)) {
        out.push({
          country,
          city,
          label: `${country.name} · ${city.name}`,
        });
      }
    }
  }
  return out;
}

export function monthOptions(count = 12): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [];
  const d = new Date();
  let y = d.getFullYear();
  let m = d.getMonth() + 1;
  const names = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
  ];
  for (let i = 0; i < count; i++) {
    const value = `${y}-${String(m).padStart(2, "0")}`;
    out.push({ value, label: `${names[m - 1]} ${y}` });
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }
  return out;
}

export function daysInMonth(ym: string): number {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}
