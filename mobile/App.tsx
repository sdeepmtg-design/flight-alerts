import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import { api, Route } from "./src/api";
import {
  COUNTRIES,
  Country,
  City,
  daysInMonth,
  monthOptions,
  searchDepartureCities,
  searchDestinations,
} from "./src/destinations";
import { describeDateFilter, describeTripClass, formatFlightDate } from "./src/format";
import { registerForPush } from "./src/notifications";

type Tab = "routes" | "settings";
type DateMode = "any" | "month" | "date";
type TripClass = 0 | 1 | 2;

function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.chip, active && styles.chipActive]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function SearchResultRow({
  label,
  sub,
  active,
  onPress,
}: {
  label: string;
  sub?: string;
  active?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.resultRow, active && styles.resultRowActive]}
      onPress={onPress}
    >
      <Text style={styles.resultLabel}>{label}</Text>
      {sub ? <Text style={styles.resultSub}>{sub}</Text> : null}
    </Pressable>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("routes");
  const [loading, setLoading] = useState(true);
  const [origin, setOrigin] = useState("MOW");
  const [routes, setRoutes] = useState<Route[]>([]);

  const [departureSearch, setDepartureSearch] = useState("");
  const [destinationSearch, setDestinationSearch] = useState("");
  const [country, setCountry] = useState<Country>(COUNTRIES[0]);
  const [city, setCity] = useState<City>(COUNTRIES[0].cities[0]);
  const [maxPrice, setMaxPrice] = useState("");
  const [dateMode, setDateMode] = useState<DateMode>("month");
  const [month, setMonth] = useState(monthOptions(1)[0].value);
  const [day, setDay] = useState(15);
  const [flex3, setFlex3] = useState(false);
  const [oneWay, setOneWay] = useState(true);
  const [tripClass, setTripClass] = useState<TripClass>(0);

  const months = useMemo(() => monthOptions(12), []);
  const days = useMemo(() => {
    const n = daysInMonth(month);
    return Array.from({ length: n }, (_, i) => i + 1);
  }, [month]);

  const filteredDepartures = useMemo(() => {
    const list = searchDepartureCities(departureSearch);
    return departureSearch.trim() ? list.slice(0, 12) : list;
  }, [departureSearch]);

  const filteredDestinations = useMemo(() => {
    const q = destinationSearch.trim();
    if (q.length < 2) return [];
    return searchDestinations(q).slice(0, 15);
  }, [destinationSearch]);

  const selectedDestination = `${country.name} · ${city.name}`;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const me = await api.getMe();
      if (me.origin_iata) setOrigin(me.origin_iata);
      setRoutes(await api.listRoutes());
    } catch (e) {
      Alert.alert("Ошибка", e instanceof Error ? e.message : "Нет связи с сервером");
    } finally {
      setLoading(false);
    }
  }, []);

  const syncPush = useCallback(async () => {
    const token = await registerForPush();
    if (token) {
      await api.updateMe({ push_token: token });
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    load();
    syncPush();
  }, [load, syncPush]);

  const saveOrigin = async () => {
    try {
      await api.updateMe({ origin_iata: origin });
      const ok = await syncPush();
      const dep = filteredDepartures.find((c) => c.iata === origin) ??
        searchDepartureCities("").find((c) => c.iata === origin);
      Alert.alert(
        "Сохранено",
        `Вылет из ${dep?.name ?? origin}` +
          (ok ? "" : "\n\nPush: нужен projectId (npx eas-cli init)"),
      );
      load();
    } catch (e) {
      Alert.alert("Ошибка", e instanceof Error ? e.message : "");
    }
  };

  const addRoute = async () => {
    const price = parseInt(maxPrice.replace(/\s/g, ""), 10);
    if (!price) {
      Alert.alert("Цена", "Укажите максимальную цену в ₽");
      return;
    }

    let departure_month: string | null = null;
    let departure_date: string | null = null;
    let date_flex_days = 0;

    if (dateMode === "month") {
      departure_month = month;
    } else if (dateMode === "date") {
      departure_month = month;
      departure_date = `${month}-${String(day).padStart(2, "0")}`;
      if (flex3) date_flex_days = 3;
    }

    try {
      await api.addRoute({
        destination_iata: city.iata,
        destination_country: country.name,
        destination_city: city.name,
        max_price: price,
        trip_class: tripClass,
        departure_month,
        departure_date,
        date_flex_days,
        one_way: oneWay,
      });
      setMaxPrice("");
      setDestinationSearch("");
      await syncPush();
      load();
      Alert.alert("Добавлено", selectedDestination);
    } catch (e) {
      Alert.alert("Ошибка", e instanceof Error ? e.message : "");
    }
  };

  const removeRoute = (id: number, title: string) => {
    Alert.alert("Удалить маршрут?", title, [
      { text: "Отмена", style: "cancel" },
      {
        text: "Удалить",
        style: "destructive",
        onPress: async () => {
          await api.deleteRoute(id);
          load();
        },
      },
    ]);
  };

  const routeTitle = (item: Route) => {
    if (item.destination_city && item.destination_country) {
      return `${item.destination_country} · ${item.destination_city}`;
    }
    return item.label || item.destination_iata;
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.root}>
        <StatusBar style="light" />
        <Text style={styles.title}>Дешёвые перелёты</Text>
        <Text style={styles.sub}>До 10 направлений · push при снижении цены</Text>

        <View style={styles.tabs}>
          <Pressable
            style={[styles.tab, tab === "routes" && styles.tabActive]}
            onPress={() => setTab("routes")}
          >
            <Text style={styles.tabText}>Маршруты</Text>
          </Pressable>
          <Pressable
            style={[styles.tab, tab === "settings" && styles.tabActive]}
            onPress={() => setTab("settings")}
          >
            <Text style={styles.tabText}>Вылет</Text>
          </Pressable>
        </View>

        {loading && routes.length === 0 ? (
          <ActivityIndicator color="#38bdf8" style={{ marginTop: 40 }} />
        ) : tab === "settings" ? (
          <View style={styles.panel}>
            <Text style={styles.section}>Откуда летите</Text>
            <TextInput
              style={styles.input}
              placeholder="Поиск города вылета…"
              placeholderTextColor="#64748b"
              value={departureSearch}
              onChangeText={setDepartureSearch}
            />
            <ScrollView style={styles.searchResults} nestedScrollEnabled>
              {filteredDepartures.map((c) => (
                <SearchResultRow
                  key={c.iata}
                  label={c.name}
                  sub={c.iata}
                  active={origin === c.iata}
                  onPress={() => setOrigin(c.iata)}
                />
              ))}
              {filteredDepartures.length === 0 && (
                <Text style={styles.hint}>Ничего не найдено</Text>
              )}
            </ScrollView>
            <Text style={styles.selectedLine}>
              Выбрано: {searchDepartureCities("").find((c) => c.iata === origin)?.name ?? origin}
            </Text>
            <Pressable style={styles.btn} onPress={saveOrigin}>
              <Text style={styles.btnText}>Сохранить</Text>
            </Pressable>
          </View>
        ) : (
          <>
            <ScrollView style={styles.formScroll} nestedScrollEnabled>
              <View style={styles.panel}>
                <Text style={styles.section}>Куда летим</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Страна или город (мин. 2 буквы)…"
                  placeholderTextColor="#64748b"
                  value={destinationSearch}
                  onChangeText={setDestinationSearch}
                />
                {filteredDestinations.length > 0 && (
                  <ScrollView style={styles.searchResults} nestedScrollEnabled>
                    {filteredDestinations.map((opt) => (
                      <SearchResultRow
                        key={`${opt.country.id}-${opt.city.iata}`}
                        label={opt.label}
                        sub={opt.city.iata}
                        active={
                          country.id === opt.country.id && city.iata === opt.city.iata
                        }
                        onPress={() => {
                          setCountry(opt.country);
                          setCity(opt.city);
                          setDestinationSearch(opt.label);
                        }}
                      />
                    ))}
                  </ScrollView>
                )}
                <Text style={styles.selectedLine}>Выбрано: {selectedDestination}</Text>

                <Text style={styles.section}>Даты</Text>
                <View style={styles.chipRow}>
                  <Chip label="4 мес." active={dateMode === "any"} onPress={() => setDateMode("any")} />
                  <Chip label="Месяц" active={dateMode === "month"} onPress={() => setDateMode("month")} />
                  <Chip label="День" active={dateMode === "date"} onPress={() => setDateMode("date")} />
                </View>

                {dateMode !== "any" && (
                  <>
                    <Text style={styles.hint}>Месяц вылета</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      <View style={styles.chipRow}>
                        {months.map((m) => (
                          <Chip
                            key={m.value}
                            label={m.label}
                            active={month === m.value}
                            onPress={() => setMonth(m.value)}
                          />
                        ))}
                      </View>
                    </ScrollView>
                  </>
                )}

                {dateMode === "date" && (
                  <>
                    <Text style={styles.hint}>День</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      <View style={styles.chipRow}>
                        {days.map((d) => (
                          <Chip
                            key={d}
                            label={String(d)}
                            active={day === d}
                            onPress={() => setDay(d)}
                          />
                        ))}
                      </View>
                    </ScrollView>
                    <Pressable style={styles.checkRow} onPress={() => setFlex3(!flex3)}>
                      <Text style={styles.checkBox}>{flex3 ? "☑" : "☐"}</Text>
                      <Text style={styles.checkLabel}>±3 дня от выбранной даты</Text>
                    </Pressable>
                  </>
                )}

                <Pressable style={styles.checkRow} onPress={() => setOneWay(true)}>
                  <Text style={styles.checkBox}>{oneWay ? "☑" : "☐"}</Text>
                  <Text style={styles.checkLabel}>Только в одну сторону</Text>
                </Pressable>
                <Pressable style={styles.checkRow} onPress={() => setOneWay(false)}>
                  <Text style={styles.checkBox}>{!oneWay ? "☑" : "☐"}</Text>
                  <Text style={styles.checkLabel}>Нужен обратный билет</Text>
                </Pressable>

                <Text style={styles.hint}>Класс</Text>
                <View style={styles.chipRow}>
                  <Chip label="Эконом" active={tripClass === 0} onPress={() => setTripClass(0)} />
                  <Chip label="Бизнес" active={tripClass === 1} onPress={() => setTripClass(1)} />
                  <Chip label="Первый" active={tripClass === 2} onPress={() => setTripClass(2)} />
                </View>
                <Text style={styles.hintSmall}>
                  Комфорт-класс в API Aviasales недоступен — только эконом, бизнес и первый.
                </Text>

                <TextInput
                  style={styles.input}
                  placeholder="Макс. цена, ₽"
                  placeholderTextColor="#64748b"
                  keyboardType="number-pad"
                  value={maxPrice}
                  onChangeText={setMaxPrice}
                />
                <Pressable style={styles.btn} onPress={addRoute}>
                  <Text style={styles.btnText}>Добавить маршрут</Text>
                </Pressable>
              </View>
            </ScrollView>

            <Text style={styles.listHeader}>Мои маршруты ({routes.length}/10)</Text>
            <FlatList
              data={routes}
              keyExtractor={(r) => String(r.id)}
              style={styles.list}
              refreshControl={
                <RefreshControl refreshing={loading} onRefresh={load} tintColor="#38bdf8" />
              }
              ListEmptyComponent={
                <Text style={styles.empty}>Добавьте направление и укажите вылет во вкладке «Вылет».</Text>
              }
              renderItem={({ item }) => {
                const dep = formatFlightDate(item.last_departure);
                const ret = formatFlightDate(item.last_return);
                const title = routeTitle(item);
                return (
                  <View style={styles.card}>
                    <View style={styles.cardHeader}>
                      <View style={styles.cardBody}>
                        <Text style={styles.cardTitle}>{title}</Text>
                        <Text style={styles.cardMeta}>
                          {describeTripClass(item.trip_class)} ·{" "}
                          {item.one_way ? "в одну сторону" : "туда-обратно"} ·{" "}
                          {describeDateFilter(item)}
                        </Text>
                        <Text style={styles.cardMeta}>
                          порог {item.max_price.toLocaleString("ru-RU")} ₽
                          {item.last_price != null
                            ? ` · ${item.last_price.toLocaleString("ru-RU")} ₽`
                            : " · ещё не проверяли"}
                        </Text>
                        {dep && (
                          <Text style={styles.cardDate}>
                            вылет {dep}
                            {!item.one_way && ret ? ` · обратно ${ret}` : ""}
                          </Text>
                        )}
                      </View>
                      <Pressable
                        style={styles.deleteBtn}
                        onPress={() => removeRoute(item.id, title)}
                        accessibilityLabel="Удалить маршрут"
                      >
                        <Text style={styles.deleteBtnText}>Удалить</Text>
                      </Pressable>
                    </View>
                  </View>
                );
              }}
            />
          </>
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0f172a", paddingHorizontal: 16 },
  title: { color: "#f8fafc", fontSize: 24, fontWeight: "700", marginTop: 4 },
  sub: { color: "#94a3b8", marginBottom: 12, fontSize: 13 },
  tabs: { flexDirection: "row", gap: 8, marginBottom: 8 },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#1e293b",
    alignItems: "center",
  },
  tabActive: { backgroundColor: "#0369a1" },
  tabText: { color: "#e2e8f0", fontWeight: "600" },
  formScroll: { maxHeight: 360, marginBottom: 4 },
  listHeader: { color: "#94a3b8", fontSize: 13, marginBottom: 6, marginTop: 4 },
  list: { flex: 1 },
  panel: { backgroundColor: "#1e293b", borderRadius: 12, padding: 12, marginBottom: 8 },
  section: { color: "#e2e8f0", fontWeight: "600", marginBottom: 6, marginTop: 4 },
  hint: { color: "#64748b", fontSize: 12, marginVertical: 6 },
  hintSmall: { color: "#475569", fontSize: 11, marginBottom: 8, lineHeight: 15 },
  selectedLine: { color: "#38bdf8", fontSize: 13, marginTop: 6, marginBottom: 4 },
  searchResults: { maxHeight: 140, marginBottom: 4 },
  resultRow: {
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: 8,
    marginBottom: 4,
    backgroundColor: "#0f172a",
  },
  resultRowActive: { backgroundColor: "#0369a1" },
  resultLabel: { color: "#f1f5f9", fontSize: 15 },
  resultSub: { color: "#94a3b8", fontSize: 12, marginTop: 2 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 6 },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
  },
  chipActive: { backgroundColor: "#0369a1", borderColor: "#0ea5e9" },
  chipText: { color: "#94a3b8", fontSize: 13 },
  chipTextActive: { color: "#f8fafc", fontWeight: "600" },
  checkRow: { flexDirection: "row", alignItems: "center", marginVertical: 6 },
  checkBox: { color: "#0ea5e9", fontSize: 18, marginRight: 8 },
  checkLabel: { color: "#e2e8f0", flex: 1 },
  input: {
    backgroundColor: "#0f172a",
    color: "#f1f5f9",
    borderRadius: 8,
    padding: 12,
    marginBottom: 6,
    fontSize: 16,
  },
  btn: {
    backgroundColor: "#0ea5e9",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    marginTop: 10,
  },
  btnText: { color: "#0f172a", fontWeight: "700" },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  cardHeader: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  cardBody: { flex: 1 },
  cardTitle: { color: "#f8fafc", fontSize: 16, fontWeight: "600" },
  cardMeta: { color: "#94a3b8", marginTop: 4, fontSize: 13 },
  cardDate: { color: "#38bdf8", marginTop: 6, fontSize: 14, fontWeight: "500" },
  deleteBtn: {
    backgroundColor: "#450a0a",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#991b1b",
  },
  deleteBtnText: { color: "#fca5a5", fontSize: 12, fontWeight: "600" },
  empty: { color: "#64748b", textAlign: "center", marginTop: 16 },
});
