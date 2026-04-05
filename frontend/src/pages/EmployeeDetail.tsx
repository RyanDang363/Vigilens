import { useEffect, useRef, useState, type FormEvent } from "react";
import { useParams, Link, useLocation, useNavigate } from "react-router-dom";
import {
  deleteEmployee,
  fetchEmployee,
  fetchEmployeeReports,
  analyzeEmployeeVideo,
  getApiErrorMessage,
  type Employee,
  type ReportSummary,
} from "../lib/api";

function normalizeConfirmName(s: string): string {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const uploadSectionRef = useRef<HTMLElement>(null);

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const [removeOpen, setRemoveOpen] = useState(false);
  const [removeAck, setRemoveAck] = useState(false);
  const [removeTypedName, setRemoveTypedName] = useState("");
  const [removeDeleting, setRemoveDeleting] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([fetchEmployee(id), fetchEmployeeReports(id)])
      .then(([emp, reps]) => {
        setEmployee(emp);
        setReports(reps);
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (location.hash !== "#end-of-day-upload") return;
    const t = window.setTimeout(() => {
      uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
    return () => window.clearTimeout(t);
  }, [location.hash, loading]);

  const handleAnalyze = async () => {
    if (!id || !videoFile || !employee) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const result = await analyzeEmployeeVideo(id, videoFile);
      const reportId = result.orchestrator?.report_id;
      const [emp, reps] = await Promise.all([
        fetchEmployee(id),
        fetchEmployeeReports(id),
      ]);
      setEmployee(emp);
      setReports(reps);
      if (reportId) {
        navigate(`/reports/${reportId}`);
      } else {
        setUploadSuccess(
          result.orchestrator
            ? "Analysis finished, but no report id was returned. Check that the orchestrator is running on port 8004."
            : "Video analyzed, but the orchestrator did not respond. Start health, efficiency, and orchestrator agents, then try again."
        );
      }
    } catch (e) {
      setUploadError(getApiErrorMessage(e));
    } finally {
      setUploading(false);
    }
  };

  const openRemoveModal = () => {
    setRemoveAck(false);
    setRemoveTypedName("");
    setRemoveError(null);
    setRemoveOpen(true);
  };

  const nameMatchesForRemoval =
    employee != null &&
    normalizeConfirmName(removeTypedName) === normalizeConfirmName(employee.name);

  const submitRemoveEmployee = async (e: FormEvent) => {
    e.preventDefault();
    if (!employee || !nameMatchesForRemoval || !removeAck) return;
    setRemoveDeleting(true);
    setRemoveError(null);
    try {
      await deleteEmployee(employee.id);
      navigate("/", { replace: true });
    } catch (err) {
      setRemoveError(getApiErrorMessage(err));
    } finally {
      setRemoveDeleting(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (!employee) return <p className="text-red-500">Employee not found.</p>;

  return (
    <div>
      <Link to="/" className="text-sm text-blue-600 hover:underline">
        &larr; Back to Roster
      </Link>

      <div className="mt-4 bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-2xl font-semibold">{employee.name}</h1>
        <p className="text-gray-500 mt-1">
          {employee.role}
          {employee.station && ` — ${employee.station}`}
        </p>
        <div className="mt-3 text-sm text-gray-600 space-y-1">
          <p>
            <span className="text-gray-500">Employee ID: </span>
            <span className="font-mono font-medium text-gray-900">{employee.id}</span>
          </p>
          {employee.email ? (
            <p>
              <span className="text-gray-500">Email: </span>
              <a
                href={`mailto:${employee.email}`}
                className="font-medium text-blue-600 hover:underline"
              >
                {employee.email}
              </a>
            </p>
          ) : (
            <p>
              <span className="text-gray-500">Email: </span>
              <span className="text-gray-400">—</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-6 mt-4 text-sm">
          <div>
            <span className="text-gray-500">Start Date: </span>
            <span className="font-medium">{employee.start_date}</span>
          </div>
          <div>
            <span className="text-gray-500">Total Infractions: </span>
            <span className="font-medium">{employee.total_findings}</span>
          </div>
          <div>
            <span className="text-gray-500">Total Reports: </span>
            <span className="font-medium">{employee.total_reports}</span>
          </div>
          {employee.total_findings > 0 && (
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${SEVERITY_COLORS[employee.highest_severity] || SEVERITY_COLORS.low}`}
            >
              Highest Severity: {employee.highest_severity.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      <section
        id="end-of-day-upload"
        ref={uploadSectionRef}
        className="mt-8 bg-gradient-to-br from-slate-50 to-blue-50/40 rounded-xl border border-gray-200 p-6"
      >
        <h2 className="text-lg font-semibold text-gray-900">
          End of workday review
        </h2>
        <p className="text-sm text-gray-600 mt-1 max-w-2xl">
          Upload a single-employee station clip from today.
        </p>

        <div className="mt-5 flex flex-col sm:flex-row sm:flex-wrap gap-4 items-start">
          <label className="block">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Video file
            </span>
            <input
              type="file"
              accept="video/*,.mov,.mp4,.webm,.mkv"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                setVideoFile(f ?? null);
                setUploadError(null);
                setUploadSuccess(null);
              }}
              className="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer disabled:opacity-50"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={!videoFile || uploading}
            onClick={handleAnalyze}
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                Analyzing video…
              </>
            ) : (
              "Generate Report"
            )}
          </button>
          {uploading && (
            <span className="text-sm text-gray-500">
              Please wait. Your report will be available shortly.
            </span>
          )}
        </div>

        {uploadError && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {uploadError}
          </p>
        )}
        {uploadSuccess && !uploadError && (
          <p className="mt-3 text-sm text-emerald-800 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
            {uploadSuccess}
          </p>
        )}
      </section>

      <h2 className="text-xl font-semibold mt-10 mb-4">Reports</h2>

      <div className="grid gap-3">
        {reports.map((r) => {
          const breakdown: string[] = [];
          if (r.code_backed_count > 0) {
            breakdown.push(`${r.code_backed_count} health`);
          }
          if (r.guidance_count > 0) {
            breakdown.push(`${r.guidance_count} guidance`);
          }
          if (r.efficiency_count > 0) {
            breakdown.push(`${r.efficiency_count} efficiency`);
          }

          return (
            <Link
              key={r.id}
              to={`/reports/${r.id}`}
              className="block bg-white rounded-lg border border-gray-200 p-4 hover:border-gray-400 transition-colors"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900">
                    {employee.name}&apos;s Report
                  </p>
                  <p className="text-sm text-gray-500">
                    {r.created_at
                      ? new Date(r.created_at).toLocaleString()
                      : "No date"}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end sm:shrink-0">
                  <span className="inline-flex items-baseline gap-1.5 rounded-full border border-gray-200/90 bg-gray-50 px-3 py-1.5 text-sm shadow-sm">
                    <span className="text-gray-500">Infractions:</span>
                    <span className="font-semibold text-gray-900 tabular-nums">
                      {r.total_findings}
                    </span>
                  </span>
                  {breakdown.length > 0 && (
                    <span className="inline-flex items-center rounded-full border border-slate-200/90 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 shadow-sm">
                      {breakdown.join(" · ")}
                    </span>
                  )}
                  <span
                    className={`shrink-0 inline-flex items-center rounded-full border border-gray-200/90 px-3 py-1.5 text-sm font-semibold shadow-sm ${SEVERITY_COLORS[r.highest_severity] || SEVERITY_COLORS.low}`}
                  >
                    {r.highest_severity.toUpperCase()}
                  </span>
                </div>
              </div>
            </Link>
          );
        })}

        {reports.length === 0 && (
          <p className="text-gray-500">No reports for this employee yet.</p>
        )}
      </div>

      <section
        className="mt-12 rounded-xl border border-red-200 bg-red-50/40 p-6"
        aria-labelledby="danger-zone-heading"
      >
        <h2 id="danger-zone-heading" className="text-lg font-semibold text-red-900">
          Remove employee
        </h2>
        <p className="text-sm text-red-800/90 mt-2 max-w-2xl">
          Removing an employee deletes them from the roster and permanently removes all of their
          reports and infractions.
        </p>
        <button
          type="button"
          onClick={openRemoveModal}
          className="mt-4 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 shadow-sm hover:bg-red-50 cursor-pointer transition-colors"
        >
          Remove employee from roster…
        </button>
      </section>

      {removeOpen && employee && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="remove-employee-title"
          onClick={() => !removeDeleting && setRemoveOpen(false)}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-gray-200"
            onClick={(ev) => ev.stopPropagation()}
          >
            <h2 id="remove-employee-title" className="text-lg font-bold text-gray-900">
              Confirm removal
            </h2>
            <p className="text-sm text-gray-600 mt-3">
              You are about to permanently delete{" "}
              <span className="font-semibold text-gray-900">{employee.name}</span>{" "}
              <span className="font-mono text-xs text-gray-500">({employee.id})</span> and all
              associated reports and infractions. This cannot be undone.
            </p>
            <form onSubmit={submitRemoveEmployee} className="mt-5 space-y-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={removeAck}
                  onChange={(e) => setRemoveAck(e.target.checked)}
                  disabled={removeDeleting}
                  className="mt-1 rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <span className="text-sm text-gray-700">
                  I understand this action is permanent and will delete all reports and infractions for
                  this employee.
                </span>
              </label>
              <div>
                <label htmlFor="remove-name-confirm" className="block text-xs font-medium text-gray-500 mb-1">
                  Type the employee&apos;s full name to confirm
                </label>
                <input
                  id="remove-name-confirm"
                  type="text"
                  value={removeTypedName}
                  onChange={(e) => setRemoveTypedName(e.target.value)}
                  placeholder={employee.name}
                  autoComplete="off"
                  disabled={removeDeleting}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                />
                {!nameMatchesForRemoval && removeTypedName.trim().length > 0 && (
                  <p className="text-xs text-amber-700 mt-1">
                    Must match their full name (capitalization and extra spaces are ignored).
                  </p>
                )}
              </div>
              {removeError && (
                <p className="text-sm text-red-600" role="alert">
                  {removeError}
                </p>
              )}
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => !removeDeleting && setRemoveOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer disabled:opacity-50"
                  disabled={removeDeleting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={removeDeleting || !removeAck || !nameMatchesForRemoval}
                  className="px-4 py-2 text-sm font-medium text-white rounded-lg bg-red-600 hover:bg-red-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {removeDeleting ? "Removing…" : "Permanently remove employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
