import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getStats, getHistory, getWeakest, generateQuiz, generateReviewQuiz } from "../api";
import type { Stats, HistorySession, WeakQuestion } from "../types";
import StatsCharts from "../components/StatsCharts";

function formatTopic(raw: string): string {
  return raw.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sessionTypeLabel(t: string): string {
  if (t === "review") return "Recapitulare";
  return "Exercitiu";
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<HistorySession[]>([]);
  const [weakest, setWeakest] = useState<WeakQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getHistory().catch(() => []),
      getWeakest().catch(() => []),
    ]).then(([s, h, w]) => {
      setStats(s);
      setHistory(h as HistorySession[]);
      setWeakest(w as WeakQuestion[]);
      setLoading(false);
    });
  }, []);

  async function handleQuickQuiz() {
    if (generating) return;
    setGenerating(true);
    setError("");
    try {
      const res = await generateQuiz({ cs_count: 30, cg_count: 0 });
      navigate(`/quiz/${res.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eroare la generarea testului");
      setGenerating(false);
    }
  }

  async function handleReviewQuiz() {
    if (generating) return;
    setGenerating(true);
    setError("");
    try {
      const res = await generateReviewQuiz({ count: 20 });
      navigate(`/quiz/${res.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eroare la generarea testului");
      setGenerating(false);
    }
  }

  if (loading) {
    return <div className="loading">Se incarca...</div>;
  }

  const hasData = stats && stats.total_answered > 0;

  const topicData = stats?.by_topic
    ? Object.entries(stats.by_topic)
        .map(([key, val]) => ({
          label: formatTopic(key),
          value: val.correct,
          total: val.total,
        }))
        .sort((a, b) => {
          const pctA = a.total ? a.value / a.total : 0;
          const pctB = b.total ? b.value / b.total : 0;
          return pctB - pctA;
        })
    : [];

  const yearData = stats?.by_year
    ? Object.entries(stats.by_year)
        .map(([key, val]) => ({
          label: key,
          value: val.correct,
          total: val.total,
        }))
        .sort((a, b) => a.label.localeCompare(b.label))
    : [];

  return (
    <div className="dashboard-page">
      <header className="dash-header">
        <div>
          <h1>Bine ai venit, {user?.username}!</h1>
          <p className="dash-subtitle">Panou de control</p>
        </div>
        <button className="btn btn-secondary" onClick={logout}>
          Deconectare
        </button>
      </header>

      {error && <div className="auth-error">{error}</div>}

      {!hasData ? (
        <div className="dash-empty">
          <h2>Nicio activitate inca</h2>
          <p>Incepe primul tau test pentru a vedea statisticile aici.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate("/quiz/setup")}
          >
            Incepe primul test
          </button>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats!.total_answered}</span>
              <span className="stat-label">Intrebari raspunse</span>
            </div>
            <div className="stat-card stat-card-accent">
              <span className="stat-value">
                {Math.round(stats!.accuracy * 100)}%
              </span>
              <span className="stat-label">Acuratete generala</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats!.total_correct}</span>
              <span className="stat-label">Raspunsuri corecte</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{history.length}</span>
              <span className="stat-label">Sesiuni completate</span>
            </div>
          </div>

          {/* Quick actions */}
          <div className="dash-section">
            <h2 className="dash-section-title">Actiuni rapide</h2>
            <div className="quick-actions">
              <button
                className="btn btn-primary"
                disabled={generating}
                onClick={handleQuickQuiz}
              >
                Test rapid 30
              </button>
              <button
                className="btn btn-primary"
                disabled={generating || weakest.length === 0}
                onClick={handleReviewQuiz}
              >
                Exerseaza punctele slabe
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => navigate("/quiz/setup")}
              >
                Test nou
              </button>
            </div>
          </div>

          {/* Charts */}
          {topicData.length > 0 && (
            <div className="dash-section">
              <StatsCharts data={topicData} title="Acuratete pe tema" />
            </div>
          )}

          {yearData.length > 0 && (
            <div className="dash-section">
              <StatsCharts data={yearData} title="Acuratete pe an" />
            </div>
          )}

          {/* Recent sessions */}
          {history.length > 0 && (
            <div className="dash-section">
              <h2 className="dash-section-title">Sesiuni recente</h2>
              <div className="history-table-wrap">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Tip</th>
                      <th>Intrebari</th>
                      <th>Scor</th>
                      <th>Acuratete</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 20).map((s) => (
                      <tr
                        key={s.session_id}
                        className="history-row"
                        onClick={() =>
                          navigate(`/quiz/${s.session_id}/results`)
                        }
                      >
                        <td>{formatDate(s.started_at)}</td>
                        <td>
                          <span className="type-badge badge-cs">
                            {sessionTypeLabel(s.session_type)}
                          </span>
                        </td>
                        <td>{s.total_questions}</td>
                        <td>
                          {s.correct}/{s.answered}
                        </td>
                        <td>{Math.round(s.accuracy * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Weakest questions */}
          {weakest.length > 0 && (
            <div className="dash-section">
              <h2 className="dash-section-title">Intrebari problematice</h2>
              <div className="weak-list">
                {weakest.slice(0, 20).map((q) => (
                  <div className="weak-item" key={q.question_id}>
                    <div className="weak-text">
                      {q.text.length > 120
                        ? q.text.slice(0, 120) + "..."
                        : q.text}
                    </div>
                    <div className="weak-meta">
                      {q.topic && (
                        <span className="topic-label">
                          {formatTopic(q.topic)}
                        </span>
                      )}
                      {q.year && (
                        <span className="year-label">{q.year}</span>
                      )}
                      <span
                        className="weak-rate"
                        style={{
                          color:
                            q.error_rate >= 0.7
                              ? "var(--color-error)"
                              : q.error_rate >= 0.5
                              ? "var(--color-warning)"
                              : "var(--color-text-muted)",
                        }}
                      >
                        {Math.round(q.error_rate * 100)}% greseli
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
