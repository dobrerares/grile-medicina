import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { generateQuiz } from "../api";
import type { AvailableCounts } from "../types";

interface LocationState {
  sources: string[];
  years: number[];
  topics: string[];
  counts: AvailableCounts | null;
}

const PRESETS = [
  { label: "10 CS", cs: 10, cg: 0 },
  { label: "20 CS", cs: 20, cg: 0 },
  { label: "30 CS", cs: 30, cg: 0 },
  { label: "30+30", cs: 30, cg: 30 },
  { label: "60 CS", cs: 60, cg: 0 },
];

export default function QuizConfig() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;

  const csMax = state?.counts?.cs_available ?? 0;
  const cgMax = state?.counts?.cg_available ?? 0;

  const [csCount, setCsCount] = useState(Math.min(30, csMax));
  const [cgCount, setCgCount] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function applyPreset(cs: number, cg: number) {
    setCsCount(Math.min(cs, csMax));
    setCgCount(Math.min(cg, cgMax));
  }

  async function handleStart() {
    if (csCount + cgCount === 0) {
      setError("Selecteaza cel putin o intrebare.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const filters: {
        sources?: string[];
        years?: number[];
        topics?: string[];
        cs_count: number;
        cg_count: number;
      } = {
        cs_count: csCount,
        cg_count: cgCount,
      };
      if (state?.sources?.length) filters.sources = state.sources;
      if (state?.years?.length) filters.years = state.years;
      if (state?.topics?.length) filters.topics = state.topics;

      const result = await generateQuiz(filters);
      navigate(`/quiz/${result.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la generare quiz");
    } finally {
      setSubmitting(false);
    }
  }

  if (!state) {
    return (
      <div className="quiz-setup-page">
        <div className="setup-card">
          <h1>Configurare Quiz - Pasul 2</h1>
          <p>Nu s-au gasit filtre. Te rog sa revii la pasul 1.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate("/quiz/setup")}
          >
            Inapoi la filtre
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="quiz-setup-page">
      <div className="setup-card">
        <h1>Configurare Quiz - Pasul 2</h1>
        <p className="setup-subtitle">Alege numarul de intrebari</p>

        <div className="available-counts">
          <span>
            CS disponibile: <strong>{csMax}</strong>
          </span>
          <span>
            CG disponibile: <strong>{cgMax}</strong>
          </span>
        </div>

        <section className="filter-section">
          <h2>Presetari</h2>
          <div className="chip-group">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                className="chip"
                onClick={() => applyPreset(p.cs, p.cg)}
                type="button"
              >
                {p.label}
              </button>
            ))}
          </div>
        </section>

        <div className="count-inputs">
          <label className="count-input-group">
            <span>Complement Simplu (CS)</span>
            <input
              type="number"
              min={0}
              max={csMax}
              value={csCount}
              onChange={(e) =>
                setCsCount(
                  Math.min(Math.max(0, Number(e.target.value)), csMax)
                )
              }
            />
            <span className="count-max">max {csMax}</span>
          </label>
          <label className="count-input-group">
            <span>Complement Grupat (CG)</span>
            <input
              type="number"
              min={0}
              max={cgMax}
              value={cgCount}
              onChange={(e) =>
                setCgCount(
                  Math.min(Math.max(0, Number(e.target.value)), cgMax)
                )
              }
            />
            <span className="count-max">max {cgMax}</span>
          </label>
        </div>

        <div className="total-selected">
          Total intrebari: <strong>{csCount + cgCount}</strong>
        </div>

        {error && <p className="auth-error">{error}</p>}

        <div className="setup-actions">
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/quiz/setup")}
            type="button"
          >
            Inapoi
          </button>
          <button
            className="btn btn-primary"
            onClick={handleStart}
            disabled={submitting || csCount + cgCount === 0}
            type="button"
          >
            {submitting ? "Se genereaza..." : "Incepe Quiz"}
          </button>
        </div>
      </div>
    </div>
  );
}
