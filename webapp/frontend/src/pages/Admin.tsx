import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  getAdminReports,
  getGrileInfo,
  uploadGrile,
  getAdminPdfs,
  uploadPdf,
  adminDeletePdf,
  resolveReport,
  deleteReport,
} from "../api";
import type { BugReport, GrileInfo, PdfFile } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  wrong_answer: "Raspuns gresit",
  typo: "Eroare in text",
  missing_answer: "Raspuns lipsa",
  app_bug: "Bug aplicatie",
  other: "Altele",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes} min in urma`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ore in urma`;
  const days = Math.floor(hours / 24);
  return `${days} zile in urma`;
}

type Tab = "reports" | "grile" | "pdfs";

export default function Admin() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("reports");

  useEffect(() => {
    if (!isAdmin) navigate("/dashboard", { replace: true });
  }, [isAdmin, navigate]);

  if (!isAdmin) return null;

  return (
    <div className="admin-page">
      <header className="admin-header">
        <h1>Admin Dashboard</h1>
        <button className="btn btn-secondary" onClick={() => navigate("/dashboard")}>
          Inapoi la app
        </button>
      </header>

      <div className="admin-tabs">
        <button className={`admin-tab ${tab === "reports" ? "admin-tab-active" : ""}`} onClick={() => setTab("reports")}>
          Bug Reports
        </button>
        <button className={`admin-tab ${tab === "grile" ? "admin-tab-active" : ""}`} onClick={() => setTab("grile")}>
          Grile.json
        </button>
        <button className={`admin-tab ${tab === "pdfs" ? "admin-tab-active" : ""}`} onClick={() => setTab("pdfs")}>
          PDFs
        </button>
      </div>

      {tab === "reports" && <ReportsTab />}
      {tab === "grile" && <GrileTab />}
      {tab === "pdfs" && <PdfsTab />}
    </div>
  );
}


function ReportsTab() {
  const [reports, setReports] = useState<BugReport[]>([]);
  const [filter, setFilter] = useState<"open" | "resolved">("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAdminReports(filter);
      setReports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function handleResolve(id: number) {
    try {
      await resolveReport(id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Sterge raportul?")) return;
    try {
      await deleteReport(id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    }
  }

  return (
    <div className="admin-tab-content">
      <div className="admin-filter-bar">
        <button
          className={`admin-pill ${filter === "open" ? "admin-pill-active" : ""}`}
          onClick={() => setFilter("open")}
        >
          Open ({filter === "open" ? reports.length : "..."})
        </button>
        <button
          className={`admin-pill ${filter === "resolved" ? "admin-pill-active" : ""}`}
          onClick={() => setFilter("resolved")}
        >
          Resolved ({filter === "resolved" ? reports.length : "..."})
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}
      {loading && <div className="admin-loading">Se incarca...</div>}

      {!loading && reports.length === 0 && (
        <div className="admin-empty">Niciun raport {filter}.</div>
      )}

      <div className="admin-report-list">
        {reports.map((r) => (
          <div key={r.id} className="admin-report-row">
            <div className="admin-report-header" onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
              <div className="admin-report-info">
                <span className="admin-report-category">{CATEGORY_LABELS[r.category] || r.category}</span>
                <span className="admin-report-question">
                  {r.question_id ? `Q ${r.question_id}` : "General"}
                </span>
                <span className="admin-report-meta">
                  {r.username || `user #${r.user_id}`} — {timeAgo(r.created_at)}
                </span>
              </div>
              <div className="admin-report-actions">
                {r.status === "open" && (
                  <button
                    className="admin-action-btn admin-action-resolve"
                    onClick={(e) => { e.stopPropagation(); handleResolve(r.id); }}
                    title="Rezolva"
                  >
                    &#10003;
                  </button>
                )}
                <button
                  className="admin-action-btn admin-action-delete"
                  onClick={(e) => { e.stopPropagation(); handleDelete(r.id); }}
                  title="Sterge"
                >
                  &#10005;
                </button>
              </div>
            </div>

            {expanded === r.id && (
              <div className="admin-report-detail">
                <p className="admin-report-description">{r.description}</p>

                {r.screenshot_path && (
                  <img
                    className="admin-report-screenshot"
                    src={`/api/admin/screenshots/${r.screenshot_path}`}
                    alt="Screenshot"
                  />
                )}

                {r.question_data && (
                  <div className="admin-question-context">
                    <h4>Detalii intrebare</h4>
                    <p className="admin-q-text">{r.question_data.text}</p>
                    <div className="admin-q-choices">
                      {Object.entries(r.question_data.choices).map(([key, val]) => (
                        <div
                          key={key}
                          className={`admin-q-choice ${key === r.question_data!.correct_answer ? "admin-q-choice-correct" : ""}`}
                        >
                          <strong>{key}.</strong> {val}
                        </div>
                      ))}
                    </div>
                    <div className="admin-q-meta">
                      <span>Tip: {r.question_data.type === "complement_grupat" ? "CG" : "CS"}</span>
                      <span>An: {r.question_data.year}</span>
                      <span>Tema: {r.question_data.topic}</span>
                      <span>Sursa: {r.question_data.source_file}</span>
                      {r.question_data.page_ref && <span>Pagina: {r.question_data.page_ref}</span>}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}


function GrileTab() {
  const [info, setInfo] = useState<GrileInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    getGrileInfo()
      .then(setInfo)
      .catch((err) => setError(err instanceof Error ? err.message : "Eroare"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!confirm("Inlocuiesti grile.json? Aceasta actiune nu poate fi anulata.")) {
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    try {
      const res = await uploadGrile(file);
      setSuccess(`Incarcat cu succes: ${res.total_questions} intrebari din ${res.source_count} surse`);
      const updated = await getGrileInfo();
      setInfo(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la incarcare");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="admin-tab-content">
      {loading && <div className="admin-loading">Se incarca...</div>}
      {error && <div className="auth-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}

      {info && (
        <div className="admin-file-info">
          <div className="admin-info-grid">
            <div className="admin-info-item">
              <span className="admin-info-label">Dimensiune</span>
              <span className="admin-info-value">{formatSize(info.file_size)}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Ultima modificare</span>
              <span className="admin-info-value">{new Date(info.last_modified).toLocaleString("ro-RO")}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Total intrebari</span>
              <span className="admin-info-value">{info.total_questions.toLocaleString()}</span>
            </div>
            <div className="admin-info-item">
              <span className="admin-info-label">Surse</span>
              <span className="admin-info-value">{info.source_count}</span>
            </div>
          </div>
        </div>
      )}

      <div className="admin-upload-section">
        <label className="btn btn-primary admin-upload-btn">
          {uploading ? "Se incarca..." : "Incarca grile.json nou"}
          <input type="file" accept=".json" onChange={handleUpload} hidden disabled={uploading} />
        </label>
      </div>
    </div>
  );
}


function PdfsTab() {
  const [pdfs, setPdfs] = useState<PdfFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAdminPdfs();
      setPdfs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await uploadPdf(file);
      setSuccess(`${file.name} incarcat cu succes`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la incarcare");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(filename: string) {
    if (!confirm(`Stergi ${filename}?`)) return;
    setError("");
    setSuccess("");
    try {
      await adminDeletePdf(filename);
      setSuccess(`${filename} sters`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la stergere");
    }
  }

  return (
    <div className="admin-tab-content">
      {error && <div className="auth-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}
      {loading && <div className="admin-loading">Se incarca...</div>}

      <div className="admin-upload-section">
        <label className="btn btn-primary admin-upload-btn">
          {uploading ? "Se incarca..." : "Incarca PDF"}
          <input type="file" accept=".pdf" onChange={handleUpload} hidden disabled={uploading} />
        </label>
      </div>

      <div className="admin-pdf-list">
        {pdfs.map((p) => (
          <div key={p.filename} className="admin-pdf-row">
            <span className="admin-pdf-name">{p.filename}</span>
            <span className="admin-pdf-size">{formatSize(p.size)}</span>
            <button
              className="admin-action-btn admin-action-delete"
              onClick={() => handleDelete(p.filename)}
              title="Sterge"
            >
              &#10005;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
