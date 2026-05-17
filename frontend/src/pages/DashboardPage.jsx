import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchHealth, setLanguage, setRole } from "../store/appSlice";
import { StatusCard } from "../components/StatusCard";

const TEXT = {
  ru: {
    title: "TeleMedHub",
    subtitle: "Платформа удалённых консультаций и мониторинга пациентов",
    lang: "Язык",
    role: "Роль",
    refresh: "Обновить",
    availability: "Доступность",
    video: "Видео задержка",
    emr: "Загрузка ЭМК",
    sessions: "Одновременные сессии",
  },
  en: {
    title: "TeleMedHub",
    subtitle: "Remote consultation and patient monitoring platform",
    lang: "Language",
    role: "Role",
    refresh: "Refresh",
    availability: "Availability",
    video: "Video latency",
    emr: "EMR loading",
    sessions: "Concurrent sessions",
  },
  kk: {
    title: "TeleMedHub",
    subtitle: "Қашықтан кеңес және пациент мониторингі платформасы",
    lang: "Тіл",
    role: "Рөл",
    refresh: "Жаңарту",
    availability: "Қолжетімділік",
    video: "Видео кідірісі",
    emr: "ЭМК жүктеу",
    sessions: "Бір мезгілдегі сессиялар",
  },
};

export function DashboardPage() {
  const dispatch = useDispatch();
  const { language, role, health, loading } = useSelector((state) => state.app);
  const t = TEXT[language];

  useEffect(() => {
    dispatch(fetchHealth());
  }, [dispatch]);

  const rows = Object.entries(health || {});

  return (
    <div className="page">
      <section className="hero">
        <div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
        <div className="controls">
          <label>
            {t.lang}
            <select value={language} onChange={(event) => dispatch(setLanguage(event.target.value))}>
              <option value="ru">RU</option>
              <option value="en">EN</option>
              <option value="kk">KK</option>
            </select>
          </label>
          <label>
            {t.role}
            <select value={role} onChange={(event) => dispatch(setRole(event.target.value))}>
              <option value="patient">Patient</option>
              <option value="doctor">Doctor</option>
              <option value="admin">Admin</option>
              <option value="insurance_representative">Insurer</option>
            </select>
          </label>
          <button onClick={() => dispatch(fetchHealth())}>{t.refresh}</button>
        </div>
      </section>

      <section className="cards">
        <StatusCard title={t.availability} value="99.9%" note="target" />
        <StatusCard title={t.video} value="< 200 ms" note="target" />
        <StatusCard title={t.emr} value="< 2 sec" note="target" />
        <StatusCard title={t.sessions} value="1000+" note="target" />
      </section>

      <section className="panel">
        <h2>Service Health</h2>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([service, info]) => (
                <tr key={service}>
                  <td>{service}</td>
                  <td>{info?.body?.status || info?.status || "unknown"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
