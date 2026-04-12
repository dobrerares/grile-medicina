import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { getSources, getTopics, getAvailableCounts } from "../api";
import type { Source, Topic, AvailableCounts } from "../types";

export default function QuizSetup() {
  const navigate = useNavigate();
  const [sources, setSources] = useState<Source[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [counts, setCounts] = useState<AvailableCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedYears, setSelectedYears] = useState<number[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([getSources(), getTopics()])
      .then(([s, t]) => {
        setSources(s);
        setTopics(t);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Eroare la incarcare")
      )
      .finally(() => setLoading(false));
  }, []);

  const fetchCounts = useCallback(() => {
    const filters: {
      sources?: string[];
      years?: number[];
      topics?: string[];
    } = {};
    if (selectedSources.length > 0) filters.sources = selectedSources;
    if (selectedYears.length > 0) filters.years = selectedYears;
    if (selectedTopics.length > 0) filters.topics = selectedTopics;

    getAvailableCounts(filters)
      .then(setCounts)
      .catch(() => {});
  }, [selectedSources, selectedYears, selectedTopics]);

  useEffect(() => {
    if (!loading) fetchCounts();
  }, [fetchCounts, loading]);

  const years = Array.from(new Set(sources.map((s) => s.year))).sort(
    (a, b) => a - b
  );

  function toggleYear(y: number) {
    setSelectedYears((prev) =>
      prev.includes(y) ? prev.filter((v) => v !== y) : [...prev, y]
    );
  }

  function toggleTopic(t: string) {
    setSelectedTopics((prev) =>
      prev.includes(t) ? prev.filter((v) => v !== t) : [...prev, t]
    );
  }

  function toggleSource(s: string) {
    setSelectedSources((prev) =>
      prev.includes(s) ? prev.filter((v) => v !== s) : [...prev, s]
    );
  }

  function handleNext() {
    navigate("/quiz/config", {
      state: {
        sources: selectedSources,
        years: selectedYears,
        topics: selectedTopics,
        counts,
      },
    });
  }

  if (loading) return <div className="loading">Se incarca...</div>;
  if (error) return <div className="page-error">{error}</div>;

  return (
    <div className="quiz-setup-page">
      <div className="setup-card">
        <h1>Configurare Quiz - Pasul 1</h1>
        <p className="setup-subtitle">Selecteaza filtrele dorite</p>

        <section className="filter-section">
          <h2>Ani</h2>
          <div className="chip-group">
            {years.map((y) => (
              <button
                key={y}
                className={`chip ${selectedYears.includes(y) ? "chip-active" : ""}`}
                onClick={() => toggleYear(y)}
                type="button"
              >
                {y}
              </button>
            ))}
          </div>
        </section>

        <section className="filter-section">
          <h2>Teme</h2>
          <div className="chip-group">
            {topics.map((t) => (
              <button
                key={t.topic}
                className={`chip ${selectedTopics.includes(t.topic) ? "chip-active" : ""}`}
                onClick={() => toggleTopic(t.topic)}
                type="button"
              >
                {t.topic} ({t.total})
              </button>
            ))}
          </div>
        </section>

        <section className="filter-section">
          <h2>Surse</h2>
          <div className="chip-group">
            {sources.map((s) => (
              <button
                key={s.file}
                className={`chip ${selectedSources.includes(s.file) ? "chip-active" : ""}`}
                onClick={() => toggleSource(s.file)}
                type="button"
              >
                {s.file} ({s.total})
              </button>
            ))}
          </div>
        </section>

        {counts && (
          <div className="available-counts">
            <span>
              CS: <strong>{counts.cs_available}</strong> disponibile
            </span>
            <span>
              CG: <strong>{counts.cg_available}</strong> disponibile
            </span>
            <span>
              Total: <strong>{counts.total_available}</strong>
            </span>
          </div>
        )}

        <div className="setup-actions">
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/dashboard")}
            type="button"
          >
            Inapoi
          </button>
          <button className="btn btn-primary" onClick={handleNext} type="button">
            Urmatorul pas
          </button>
        </div>
      </div>
    </div>
  );
}
