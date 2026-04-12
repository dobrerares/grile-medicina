import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { completeQuiz, generateReviewQuiz } from "../api";

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

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CompletionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    completeQuiz(Number(sessionId))
      .then((res) => setData(res as CompletionResult))
      .catch(async (err) => {
        // If already completed (400), try fetching via complete again or show error
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

  return (
    <div className="results-page">
      <div className="results-card">
        <h1>Rezultate</h1>

        <div className="results-summary">
          <div className="score-display">
            <span className="score-number">{data.correct_count}</span>
            <span className="score-divider">/</span>
            <span className="score-total">{data.total_questions}</span>
          </div>
          <div className="accuracy-bar">
            <div
              className="accuracy-fill"
              style={{
                width: `${pct}%`,
                background:
                  pct >= 70
                    ? "var(--color-success)"
                    : pct >= 50
                      ? "var(--color-warning)"
                      : "var(--color-error)",
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

        <div className="results-actions">
          {wrongCount > 0 && (
            <button
              className="btn btn-primary"
              onClick={handleReviewMistakes}
              disabled={reviewLoading}
              type="button"
            >
              {reviewLoading ? "Se genereaza..." : `Revizuieste greseli (${wrongCount})`}
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

        <h2 className="results-list-title">Detalii intrebari</h2>
        <div className="results-list">
          {data.results.map((r) => {
            const isCG = r.type === "complement_grupat";
            const rowClass = r.user_answer === null
              ? "result-row result-unanswered"
              : r.is_correct
                ? "result-row result-correct"
                : "result-row result-wrong";
            const expanded = expandedId === r.question_id;

            return (
              <div key={r.question_id} className={rowClass}>
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
