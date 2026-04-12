import { useState } from "react";
import type { SessionQuestion, AnswerResult } from "../types";
import ReportModal from "./ReportModal";

const CG_LEGEND: Record<string, string> = {
  A: "afirmatiile 1, 2, 3 sunt corecte",
  B: "afirmatiile 1, 3 sunt corecte",
  C: "afirmatiile 2, 4 sunt corecte",
  D: "numai afirmatia 4 este corecta",
  E: "toate afirmatiile sunt corecte",
};

interface QuestionCardProps {
  question: SessionQuestion;
  selectedAnswer: string | null;
  onSelectAnswer: (answer: string) => void;
  onConfirm: () => void;
  result: AnswerResult | null;
  sourceFile?: string;
  pageRef?: string;
  examMode?: boolean;
}

export default function QuestionCard({
  question,
  selectedAnswer,
  onSelectAnswer,
  onConfirm,
  result,
  sourceFile,
  pageRef,
  examMode,
}: QuestionCardProps) {
  const [showReport, setShowReport] = useState(false);
  const isCG = question.type === "complement_grupat";
  const showResult = result !== null;
  const confirmed = showResult || question.answered;

  // Separate statement choices (1-4) from answer choices (A-E) for CG
  const statementKeys = isCG
    ? Object.keys(question.choices).filter((k) => /^\d+$/.test(k))
    : [];
  const answerKeys = isCG
    ? ["A", "B", "C", "D", "E"]
    : Object.keys(question.choices).sort();

  function getChoiceClass(key: string): string {
    if (!showResult) {
      return selectedAnswer === key ? "choice-selected anim-pop" : "";
    }
    const classes: string[] = [];
    if (key === result.correct_answer) {
      classes.push("choice-correct");
      classes.push("anim-correct-glow");
    }
    if (
      selectedAnswer === key &&
      key !== result.correct_answer
    ) {
      classes.push("choice-wrong");
      classes.push("anim-shake");
    }
    if (selectedAnswer === key) {
      classes.push("choice-selected");
    }
    return classes.join(" ");
  }

  function handlePdfOpen() {
    if (!sourceFile) return;
    let page = 1;
    if (pageRef) {
      const match = pageRef.match(/(\d+)/);
      if (match) page = parseInt(match[1], 10);
    }
    const url =
      "/api/pdf/" +
      encodeURIComponent(sourceFile + ".pdf") +
      "#page=" +
      page;
    window.open(url, "_blank");
  }

  return (
    <div className="question-card">
      <div className="question-header">
        <span className="question-number">
          Intrebarea {question.position}
        </span>
        <span className={`type-badge ${isCG ? "badge-cg" : "badge-cs"}`}>
          {isCG ? "CG" : "CS"}
        </span>
        {question.topic && (
          <span className="topic-label">{question.topic}</span>
        )}
        {question.year && (
          <span className="year-label">{question.year}</span>
        )}
        {pageRef && (
          <span className="page-label">{pageRef}</span>
        )}
        <button
          className="report-flag-btn"
          onClick={() => setShowReport(true)}
          title="Raporteaza o problema"
          type="button"
        >
          &#9873;
        </button>
      </div>

      <p className="question-text">{question.text}</p>

      {isCG && statementKeys.length > 0 && (
        <ol className="cg-statements">
          {statementKeys.map((k) => (
            <li
              key={k}
              className={
                showResult && result.correct_statements?.includes(Number(k))
                  ? "statement-correct"
                  : ""
              }
            >
              {question.choices[k]}
            </li>
          ))}
        </ol>
      )}

      <div className="choices-list">
        {answerKeys.map((key) => (
          <label
            key={key}
            className={`choice-row ${getChoiceClass(key)}`}
          >
            <input
              type="radio"
              name={`q-${question.session_question_id}`}
              value={key}
              checked={selectedAnswer === key}
              onChange={() => onSelectAnswer(key)}
              disabled={confirmed}
            />
            <span className="choice-letter">{key}</span>
            <span className="choice-text">
              {isCG ? CG_LEGEND[key] : question.choices[key]}
            </span>
          </label>
        ))}
      </div>

      {showResult && result.correct_statements && (
        <div className="correct-statements-info">
          Afirmatii corecte: {result.correct_statements.join(", ")}
        </div>
      )}

      <div className="question-actions">
        {!confirmed && !examMode && (
          <button
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={!selectedAnswer}
          >
            Confirma
          </button>
        )}
        {sourceFile && (
          <button
            className="btn btn-secondary"
            onClick={handlePdfOpen}
            type="button"
          >
            Vezi in PDF
          </button>
        )}
      </div>
      {showReport && (
        <ReportModal
          onClose={() => setShowReport(false)}
          questionId={question.question_id}
          sourceFile={sourceFile}
          pageRef={pageRef}
        />
      )}
    </div>
  );
}
