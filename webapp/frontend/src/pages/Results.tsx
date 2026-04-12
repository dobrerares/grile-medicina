import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { completeQuiz, generateReviewQuiz } from "../api";
import { getResultBanner } from "../messages";
import Confetti from "../components/Confetti";

interface QuestionResult {
  question_id: string;
  position: number;
  text: string;
  type: string;
  choices: Record<string, string>;
  correct_answer: string;
  correct_statements: number[] | null;
  user_answer: string | null;
  is_correct: boolean;
  time_spent_ms: number | null;
}

interface CompletionResult {
  session_id: number;
  completed_at: string;
  total_questions: number;
  total_answered: number;
  correct_count: number;
  accuracy: number;
  results: QuestionResult[];
}

function useCountUp(target: number, duration = 1000): number {
  const [value, setValue] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number>(0);

  const animate = useCallback(
    (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    },
    [target, duration]
  );

  useEffect(() => {
    if (target === 0) return;
    startRef.current = null;
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, animate]);

  return value;
}

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CompletionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [barAnimated, setBarAnimated] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    completeQuiz(Number(sessionId))
      .then((res) => setData(res as CompletionResult))
      .catch(async (err) => {
        if (err instanceof Error && err.message.includes("400")) {
          try {
            const res = await completeQuiz(Number(sessionId));
            setData(res as CompletionResult);
          } catch {
            setError("Nu s-au putut incarca rezultatele.");
          }
        } else {
          setError(
            err instanceof Error ? err.message : "Eroare la incarcarea rezultatelor"
          );
        }
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    if (data) {
      const timer = setTimeout(() => setBarAnimated(true), 100);
      return () => clearTimeout(timer);
    }
  }, [data]);

  const displayCount = useCountUp(data?.correct_count ?? 0);

  async function handleReviewMistakes() {
    if (!data) return;
    const wrongCount = data.results.filter((r) => !r.is_correct).length;
    if (wrongCount === 0) return;
    setReviewLoading(true);
    try {
      const result = await generateReviewQuiz({ count: wrongCount });
      navigate(`/quiz/${result.session_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Eroare la generare review"
      );
    } finally {
      setReviewLoading(false);
    }
  }

  if (loading) return <div className="loading">Se incarca rezultatele...</div>;
  if (error) return <div className="page-error">{error}</div>;
  if (!data) return <div className="page-error">Rezultate indisponibile.</div>;

  const pct = Math.round(data.accuracy * 100);
  const wrongCount = data.results.filter((r) => !r.is_correct).length;
  const unansweredCount = data.results.filter(
    (r) => r.user_answer === null
  ).length;
  const banner = getResultBanner(data.accuracy);
  const showConfetti = data.accuracy >= 0.9;

  return (
    <div className="results-page">
      {showConfetti && <Confetti />}
      <div className="results-card">
        <h1 className="anim-fade-slide-up">Rezultate</h1>

        <div className={`results-banner results-banner-${banner.tone} anim-fade-slide-up`} style={{ animationDelay: "0.1s" }}>
          {banner.text}
        </div>

        <div className="results-summary anim-fade-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="score-display anim-count-up">
            <span className="score-number">{displayCount}</span>
            <span className="score-divider">/</span>
            <span className="score-total">{data.total_questions}</span>
          </div>
          <div className="accuracy-bar">
            <div
              className="accuracy-fill"
              style={{
                width: barAnimated ? `${pct}%` : "0%",
                background:
                  pct >= 70
                    ? "var(--color-success)"
                    : pct >= 50
                      ? "var(--color-warning)"
                      : "var(--color-error)",
                transition: "width 1s cubic-bezier(0.34, 1.56, 0.64, 1)",
              }}
            />
          </div>
          <div className="accuracy-label">{pct}% corect</div>
          <div className="results-meta">
            <span>Raspunse: {data.total_answered}</span>
            {unansweredCount > 0 && (
              <span>Fara raspuns: {unansweredCount}</span>
            )}
            <span>Gresite: {wrongCount}</span>
          </div>
        </div>

        <div className="results-actions anim-fade-slide-up" style={{ animationDelay: "0.3s" }}>
          {wrongCount > 0 && (
            <button
              className="btn btn-primary"
              onClick={handleReviewMistakes}
              disabled={reviewLoading}
              type="button"
            >
              {reviewLoading ? "Se genereaza..." : `Exerseaza punctele slabe (${wrongCount})`}
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/dashboard")}
            type="button"
          >
            Inapoi la Dashboard
          </button>
        </div>

        <h2 className="results-list-title anim-fade-slide-up" style={{ animationDelay: "0.4s" }}>Detalii intrebari</h2>
        <div className="results-list">
          {data.results.map((r, i) => {
            const isCG = r.type === "complement_grupat";
            const rowClass = r.user_answer === null
              ? "result-row result-unanswered"
              : r.is_correct
                ? "result-row result-correct"
                : "result-row result-wrong";
            const expanded = expandedId === r.question_id;

            return (
              <div
                key={r.question_id}
                className={`${rowClass} anim-fade-slide-up`}
                style={{ animationDelay: `${0.4 + Math.min(i, 10) * 0.03}s` }}
              >
                <div
                  className="result-row-header"
                  onClick={() =>
                    setExpandedId(expanded ? null : r.question_id)
                  }
                >
                  <span className="result-position">{r.position}.</span>
                  <span className="result-text-preview">
                    {r.text.length > 100
                      ? r.text.slice(0, 100) + "..."
                      : r.text}
                  </span>
                  <span
                    className={`type-badge ${isCG ? "badge-cg" : "badge-cs"}`}
                  >
                    {isCG ? "CG" : "CS"}
                  </span>
                  <span className="result-answers">
                    {r.user_answer ?? "-"} / {r.correct_answer}
                  </span>
                  <span className="result-expand">
                    {expanded ? "\u25B2" : "\u25BC"}
                  </span>
                </div>
                {expanded && (
                  <div className="result-row-detail">
                    <p className="detail-question-text">{r.text}</p>
                    <div className="detail-choices">
                      {Object.entries(r.choices).map(([key, val]) => {
                        let cls = "detail-choice";
                        if (key === r.correct_answer) cls += " detail-correct";
                        if (
                          key === r.user_answer &&
                          key !== r.correct_answer
                        )
                          cls += " detail-wrong";
                        return (
                          <div key={key} className={cls}>
                            <strong>{key}.</strong> {val}
                          </div>
                        );
                      })}
                    </div>
                    {r.correct_statements && (
                      <p className="detail-statements">
                        Afirmatii corecte: {r.correct_statements.join(", ")}
                      </p>
                    )}
                    {r.time_spent_ms != null && (
                      <p className="detail-time">
                        Timp: {(r.time_spent_ms / 1000).toFixed(1)}s
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
