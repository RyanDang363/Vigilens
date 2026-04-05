import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { useParams, Link } from "react-router-dom";
import {
  fetchEmployee,
  fetchReport,
  fetchGoogleStatus,
  logFindingsToSheet,
  type Report,
  type GoogleStatus,
} from "../lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-700 border-gray-200",
  medium: "bg-yellow-50 text-yellow-900 border-yellow-200",
  high: "bg-orange-50 text-orange-900 border-orange-200",
  critical: "bg-red-50 text-red-900 border-red-200",
};

const SEVERITY_BADGE: Record<string, string> = {
  low: "bg-gray-100 text-gray-700",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const CLASS_BADGE: Record<string, string> = {
  code_backed_food_safety: "bg-blue-100 text-blue-800",
  workplace_safety_rule: "bg-purple-100 text-purple-800",
  efficiency: "bg-teal-100 text-teal-800",
  house_rule: "bg-gray-100 text-gray-700",
};

const CLASS_LABEL: Record<string, string> = {
  code_backed_food_safety: "Health Code",
  workplace_safety_rule: "Workplace Safety",
  efficiency: "Efficiency",
  house_rule: "House Rule",
};

const ACTION_LABELS: Record<string, string> = {
  send_email: "Email Report",
  log_sheet: "Google Sheets Log",
  get_training_docs: "Training Document Search",
  research_violations: "Regulatory Research",
};

const ACTION_ICONS: Record<string, string> = {
  send_email: "\u2709\uFE0F",
  log_sheet: "\uD83D\uDCC4",
  get_training_docs: "\uD83D\uDCDA",
  research_violations: "\uD83D\uDD0D",
};

const ACTION_HEADER_STYLE: Record<string, string> = {
  send_email: "bg-blue-100",
  log_sheet: "bg-green-100",
  get_training_docs: "bg-purple-100",
  research_violations: "bg-amber-100",
};

const ACTION_DESCRIPTIONS: Record<string, string> = {
  send_email: "Sent safety report to employee via email",
  log_sheet: "Logged findings to connected Google Sheet",
  get_training_docs: "Searched uploaded training materials for relevant content",
  research_violations: "Researched FDA, OSHA, and CDC regulations with training videos",
};

function formatType(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [employeeName, setEmployeeName] = useState<string | null>(null);
  const [google, setGoogle] = useState<GoogleStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [sheetMsg, setSheetMsg] = useState("");
  const [sheetLoading, setSheetLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([fetchReport(id), fetchGoogleStatus()])
      .then(async ([r, g]) => {
        setReport(r);
        setGoogle(g);
        try {
          const emp = await fetchEmployee(r.employee_id);
          setEmployeeName(emp.name);
        } catch {
          setEmployeeName(null);
        }
      })
      .catch(() => {
        setReport(null);
        setEmployeeName(null);
        setGoogle(null);
      })
      .finally(() => setLoading(false));
  }, [id]);

  const handleLogToSheet = async () => {
    if (!report) return;
    setSheetLoading(true);
    setSheetMsg("");
    try {
      const result = await logFindingsToSheet(report.id);
      setSheetMsg(
        `${result.rows_appended} findings logged to Google Sheet.`
      );
    } catch {
      setSheetMsg("Failed to log findings to sheet.");
    } finally {
      setSheetLoading(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (!report) return <p className="text-red-500">Report not found.</p>;

  return (
    <div>
      <Link
        to={`/employees/${report.employee_id}`}
        className="text-sm text-blue-600 hover:underline"
      >
        &larr; Back to Employee
      </Link>

      {/* Summary bar */}
      <div className="mt-4 bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">
              {employeeName ? `${employeeName}'s Report` : "Report"}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {report.jurisdiction.toUpperCase()} jurisdiction
              {report.created_at &&
                ` — ${new Date(report.created_at).toLocaleString()}`}
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${SEVERITY_BADGE[report.highest_severity]}`}
            >
              Highest: {report.highest_severity.toUpperCase()}
            </span>
            <span className="text-gray-500">
              {report.findings.length} finding
              {report.findings.length !== 1 && "s"}
            </span>
          </div>
        </div>

        <div className="flex gap-4 mt-3 text-xs">
          {report.code_backed_count > 0 && (
            <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">
              {report.code_backed_count} health code
            </span>
          )}
          {report.guidance_count > 0 && (
            <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700">
              {report.guidance_count} workplace safety
            </span>
          )}
          {report.efficiency_count > 0 && (
            <span className="px-2 py-0.5 rounded bg-teal-50 text-teal-700">
              {report.efficiency_count} efficiency
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-4">
          {google?.connected && google.sheet_id ? (
            <button
              onClick={handleLogToSheet}
              disabled={sheetLoading}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 cursor-pointer transition-colors"
            >
              {sheetLoading ? "Logging..." : "Log to Google Sheet"}
            </button>
          ) : (
            <Link
              to="/settings"
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Connect Google to log findings
            </Link>
          )}
          {google?.sheet_url && (
            <a
              href={google.sheet_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              Open Sheet
            </a>
          )}
        </div>
        {sheetMsg && (
          <p className="mt-2 text-sm text-green-700">{sheetMsg}</p>
        )}
      </div>

      {/* Findings */}
      <h2 className="text-lg font-semibold mt-8 mb-4">Findings</h2>

      <div className="grid gap-4">
        {report.findings.map((f) => (
          <div
            key={f.id}
            className={`rounded-lg border p-5 ${SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.low}`}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-base">
                  {formatType(f.concluded_type)}
                </h3>
                <div className="flex gap-2 mt-1.5">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${CLASS_BADGE[f.finding_class] || CLASS_BADGE.house_rule}`}
                  >
                    {CLASS_LABEL[f.finding_class] || f.finding_class}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_BADGE[f.severity]}`}
                  >
                    {f.severity.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="text-right text-xs text-gray-500">
                <p>
                  {f.timestamp_start} — {f.timestamp_end}
                </p>
              </div>
            </div>

            <div className="mt-3 text-sm">
              <span className="font-medium text-gray-800">
                Infraction recorded:{" "}
              </span>
              <span>{f.reasoning}</span>
            </div>

            {/* Policy citation */}
            <div className="mt-3 text-xs">
              <span className="font-medium">Policy violated: </span>
              {f.policy_url ? (
                <a
                  href={f.policy_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-700 underline"
                >
                  {f.policy_code} — {f.policy_section}
                </a>
              ) : (
                <span>
                  {f.policy_code} — {f.policy_section}
                </span>
              )}
            </div>
            <p className="text-xs mt-1 italic">{f.policy_short_rule}</p>

            <div className="mt-3 p-3 bg-white/50 rounded text-sm">
              <span className="font-medium">Mitigation: </span>
              {f.training_recommendation}
            </div>

            {f.corrective_action_observed && (
              <p className="mt-2 text-xs text-green-700">
                Corrective action was observed.
              </p>
            )}
          </div>
        ))}

        {report.findings.length === 0 && (
          <p className="text-gray-500">No findings in this report.</p>
        )}
      </div>

      {/* Agent Action Results */}
      {report.action_logs && report.action_logs.length > 0 && (
        <>
          <h2 className="text-lg font-semibold mt-8 mb-4">Agent Actions</h2>
          <div className="space-y-3">
            {report.action_logs.map((log) => {
              const hasContent =
                log.full_output && log.full_output.length > 0;
              const isLong = log.full_output.length > 200;

              return (
                <div
                  key={log.id}
                  className={`rounded-xl border overflow-hidden ${
                    log.success
                      ? "border-gray-200"
                      : "border-red-200 bg-red-50/30"
                  }`}
                >
                  {/* Header — always visible */}
                  <div
                    className={`flex items-center gap-3 px-4 py-3 ${
                      log.success ? "bg-gray-50" : "bg-red-50/50"
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 ${
                        ACTION_HEADER_STYLE[log.action_type] ||
                        "bg-gray-100"
                      }`}
                    >
                      {ACTION_ICONS[log.action_type] || ""}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900">
                          {ACTION_LABELS[log.action_type] || log.action_type}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${
                            log.status === "in_progress"
                              ? "bg-blue-100 text-blue-700 animate-pulse"
                              : log.success
                                ? "bg-green-100 text-green-700"
                                : "bg-red-100 text-red-700"
                          }`}
                        >
                          {log.status === "in_progress"
                            ? "Running"
                            : log.success
                              ? "Done"
                              : "Failed"}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {ACTION_DESCRIPTIONS[log.action_type] || ""}
                      </p>
                    </div>
                    {log.recording_url && (
                      <a
                        href={log.recording_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-blue-600 hover:text-blue-800 shrink-0"
                      >
                        View Recording
                      </a>
                    )}
                  </div>

                  {/* Body */}
                  {hasContent && (
                    <div className="bg-white">
                      {isLong ? (
                        <details className="group">
                          <summary className="px-4 py-2.5 text-xs font-medium text-blue-600 cursor-pointer select-none hover:bg-blue-50/50 transition-colors flex items-center gap-1">
                            <svg
                              className="w-3.5 h-3.5 transition-transform group-open:rotate-90"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2.5}
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M9 5l7 7-7 7"
                              />
                            </svg>
                            View full output
                          </summary>
                          <div className="px-4 pb-4 max-h-[600px] overflow-y-auto">
                            <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:mt-4 prose-headings:mb-2 prose-p:text-gray-700 prose-p:my-1.5 prose-a:text-blue-600 prose-strong:text-gray-800 prose-blockquote:border-blue-300 prose-blockquote:bg-blue-50/50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded prose-blockquote:text-gray-600 prose-blockquote:not-italic prose-hr:border-gray-200 prose-hr:my-3 prose-table:text-sm prose-li:my-0.5">
                              <Markdown>{log.full_output}</Markdown>
                            </div>
                          </div>
                        </details>
                      ) : (
                        <div className="px-4 py-3">
                          <div className="prose prose-sm max-w-none prose-p:text-gray-700 prose-p:my-1 prose-strong:text-gray-800 prose-a:text-blue-600">
                            <Markdown>{log.full_output}</Markdown>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
