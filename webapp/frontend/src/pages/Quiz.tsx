import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { getQuiz, submitAnswer, completeQuiz } from "../api";
import type { QuizDetail, SessionQuestion, AnswerResult } from "../types";
import QuestionCard from "../components/QuestionCard";
import ComplementGrupatInfo from "../components/ComplementGrupatInfo";

export default function Quiz() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<
    Record<number, { selected: string; result: AnswerResult }>
  >({});
  const [pendingAnswer, setPendingAnswer] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const examMode =
    (location.state as { hideResults?: boolean } | null)?.hideResults ?? false;
  const [examSelections, setExamSelections] = useState<
    Record<number, string>
  >({});
  const timerRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    getQuiz(Number(sessionId))
      .then((data) => {
        setQuiz(data);
        // Restore already-answered questions
        const restored: Record<
          number,
          { selected: string; result: AnswerResult }
        > = {};
        data.questions.forEach((q) => {
          if (q.answered && q.user_answer) {
            restored[q.session_question_id] = {
              selected: q.user_answer,
              result: {
                is_correct: false, // unknown until re-fetched but marking as answered
                correct_answer: "",
              },
            };
          }
        });
        setAnswers(restored);
        // Jump to first unanswered question when resuming
        const firstUnanswered = data.questions.findIndex(
          (q) => !q.answered && !q.user_answer
        );
        if (firstUnanswered > 0) {
          setCurrentIndex(firstUnanswered);
        }
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Eroare")
      )
      .finally(() => setLoading(false));
  }, [sessionId]);

  // Reset timer when navigating to a new question
  useEffect(() => {
    timerRef.current = Date.now();
  }, [currentIndex]);

  const questions: SessionQuestion[] = quiz?.questions ?? [];
  const currentQuestion = questions[currentIndex] ?? null;
  const currentAnswer = currentQuestion
    ? answers[currentQuestion.session_question_id]
    : undefined;

  const handleConfirm = useCallback(async () => {
    if (!currentQuestion || !pendingAnswer || !sessionId) return;
    setSubmitting(true);
    const timeMs = Date.now() - timerRef.current;
    try {
      const result = await submitAnswer(
        Number(sessionId),
        currentQuestion.question_id,
        pendingAnswer,
        timeMs
      );
      setAnswers((prev) => ({
        ...prev,
        [currentQuestion.session_question_id]: {
          selected: pendingAnswer,
          result,
        },
      }));
      // Mark answered locally
      setQuiz((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          questions: prev.questions.map((q) =>
            q.session_question_id === currentQuestion.session_question_id
              ? { ...q, answered: true, user_answer: pendingAnswer }
              : q
          ),
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la trimitere");
    } finally {
      setSubmitting(false);
    }
  }, [currentQuestion, pendingAnswer, sessionId]);

  async function handleFinish() {
    if (!sessionId) return;
    setFinishing(true);
    try {
      if (examMode) {
        // Submit all locally-stored answers at once
        await Promise.all(
          Object.entries(examSelections).map(([sqId, answer]) => {
            const q = questions.find(
              (q) => q.session_question_id === Number(sqId)
            );
            if (q) {
              return submitAnswer(
                Number(sessionId),
                q.question_id,
                answer
              );
            }
          })
        );
      }
      await completeQuiz(Number(sessionId));
      navigate(`/quiz/${sessionId}/results`);
    } catch {
      // Already completed — go to results anyway
      navigate(`/quiz/${sessionId}/results`);
    }
  }

  function goTo(idx: number) {
    setPendingAnswer(null);
    setCurrentIndex(idx);
  }

  if (loading) return <div className="loading">Se incarca quiz-ul...</div>;
  if (error) return <div className="page-error">{error}</div>;
  if (!quiz || questions.length === 0) {
    return <div className="page-error">Quiz-ul nu a fost gasit.</div>;
  }

  const answeredCount = examMode
    ? Object.keys(examSelections).length
    : questions.filter(
        (q) => q.answered || answers[q.session_question_id]
      ).length;
  const progressPct = Math.round((answeredCount / questions.length) * 100);

  // Extract source_file from question_id: e.g. "2025_celula_1_q1" → need from quiz data
  // The question_id encodes info but source_file isn't directly available on SessionQuestion.
  // We don't have source_file/page_ref on SessionQuestion — these buttons won't work without them.

  return (
    <div className="quiz-page">
      <div className="quiz-sidebar">
        <div className="sidebar-header">
          <h3>Intrebari</h3>
          <span className="sidebar-progress">
            {answeredCount}/{questions.length}
          </span>
        </div>
        <div className="question-nav-grid">
          {questions.map((q, idx) => {
            const ans = answers[q.session_question_id];
            let cls = "nav-btn";
            if (idx === currentIndex) cls += " nav-current";
            if (!examMode && ans) {
              cls += ans.result.is_correct ? " nav-correct" : " nav-wrong";
            } else if (
              examMode
                ? examSelections[q.session_question_id]
                : ans || q.answered
            ) {
              cls += " nav-answered";
            }
            return (
              <button
                key={q.session_question_id}
                className={cls}
                onClick={() => goTo(idx)}
                type="button"
              >
                {q.position}
              </button>
            );
          })}
        </div>
        <ComplementGrupatInfo />
      </div>

      <div className="quiz-main">
        <div className="quiz-top-bar">
          <div className="quiz-progress-info">
            Intrebarea {currentIndex + 1} din {questions.length}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <button
            className="btn btn-danger finish-btn"
            onClick={handleFinish}
            disabled={finishing}
            type="button"
          >
            {finishing ? "Se finalizeaza..." : "Finalizeaza Quiz"}
          </button>
        </div>

        {currentQuestion && (
          <QuestionCard
            question={currentQuestion}
            selectedAnswer={
              examMode
                ? examSelections[currentQuestion.session_question_id] ?? null
                : currentAnswer?.selected ?? pendingAnswer
            }
            onSelectAnswer={(a) => {
              if (examMode) {
                const isFirst =
                  !examSelections[currentQuestion.session_question_id];
                setExamSelections((prev) => ({
                  ...prev,
                  [currentQuestion.session_question_id]: a,
                }));
                if (isFirst && currentIndex < questions.length - 1) {
                  goTo(currentIndex + 1);
                }
              } else {
                if (!currentAnswer) setPendingAnswer(a);
              }
            }}
            onConfirm={handleConfirm}
            result={examMode ? null : (currentAnswer?.result ?? null)}
            sourceFile={currentQuestion.source_file}
            pageRef={currentQuestion.page_ref}
            examMode={examMode}
          />
        )}

        {submitting && <div className="submitting-overlay">Se trimite...</div>}

        <div className="quiz-nav-buttons">
          <button
            className="btn btn-secondary"
            onClick={() => goTo(currentIndex - 1)}
            disabled={currentIndex === 0}
            type="button"
          >
            Anterioara
          </button>
          <button
            className="btn btn-primary"
            onClick={() => goTo(currentIndex + 1)}
            disabled={currentIndex >= questions.length - 1}
            type="button"
          >
            Urmatoarea
          </button>
        </div>
      </div>
    </div>
  );
}
