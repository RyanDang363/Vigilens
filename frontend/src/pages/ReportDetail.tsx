import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchReport, type Report } from "../lib/api";

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

function formatType(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetchReport(id)
      .then(setReport)
      .finally(() => setLoading(false));
  }, [id]);

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
              Report — {report.clip_id || "N/A"}
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

            {/* Reasoning */}
            <p className="mt-3 text-sm">{f.reasoning}</p>

            {/* Policy citation */}
            <div className="mt-3 text-xs">
              <span className="font-medium">Policy: </span>
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

            {/* Coaching */}
            <div className="mt-3 p-3 bg-white/50 rounded text-sm">
              <span className="font-medium">Coaching: </span>
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
    </div>
  );
}
