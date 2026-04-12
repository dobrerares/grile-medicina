import { useState, useRef } from "react";
import { submitReport } from "../api";

const CATEGORIES = [
  { value: "wrong_answer", label: "Raspuns gresit" },
  { value: "typo", label: "Eroare in text" },
  { value: "missing_answer", label: "Raspuns lipsa" },
  { value: "app_bug", label: "Bug aplicatie" },
  { value: "other", label: "Altele" },
];

interface ReportModalProps {
  onClose: () => void;
  questionId?: string;
  sourceFile?: string;
  pageRef?: string;
  defaultCategory?: string;
}

export default function ReportModal({
  onClose,
  questionId,
  sourceFile,
  pageRef,
  defaultCategory,
}: ReportModalProps) {
  const [category, setCategory] = useState(defaultCategory || (questionId ? "wrong_answer" : "app_bug"));
  const [description, setDescription] = useState("");
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;

    setSubmitting(true);
    setError("");

    const form = new FormData();
    form.append("category", category);
    form.append("description", description.trim());
    if (questionId) {
      form.append("question_id", questionId);
    }
    if (screenshot) {
      form.append("screenshot", screenshot);
    }

    try {
      await submitReport(form);
      setSuccess(true);
      setTimeout(onClose, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la trimitere");
    } finally {
      setSubmitting(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Fisierul trebuie sa fie sub 5 MB");
      return;
    }
    setScreenshot(file);
    setError("");
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Raporteaza o problema</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {success ? (
          <div className="report-success">Raportul a fost trimis!</div>
        ) : (
          <form onSubmit={handleSubmit}>
            {questionId && (
              <div className="report-context">
                <span className="report-context-label">Intrebare:</span> {questionId}
                {sourceFile && <><br /><span className="report-context-label">Sursa:</span> {sourceFile}</>}
                {pageRef && <><br /><span className="report-context-label">Pagina:</span> {pageRef}</>}
              </div>
            )}

            <label className="report-field">
              <span>Categorie</span>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </label>

            <label className="report-field">
              <span>Descriere</span>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descrie problema..."
                rows={4}
                required
              />
            </label>

            <label className="report-field">
              <span>Captura de ecran (optional)</span>
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
              />
              {screenshot && (
                <span className="report-file-name">{screenshot.name}</span>
              )}
            </label>

            {error && <div className="auth-error">{error}</div>}

            <div className="report-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Anuleaza</button>
              <button type="submit" className="btn btn-primary" disabled={submitting || !description.trim()}>
                {submitting ? "Se trimite..." : "Trimite"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
