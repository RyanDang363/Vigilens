import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchEmployee,
  fetchEmployeeReports,
  type Employee,
  type ReportSummary,
} from "../lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-700",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export default function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([fetchEmployee(id), fetchEmployeeReports(id)])
      .then(([emp, reps]) => {
        setEmployee(emp);
        setReports(reps);
      })
      .finally(() => setLoading(false));
  }, [id]);

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
        <div className="flex gap-6 mt-4 text-sm">
          <div>
            <span className="text-gray-500">Start Date: </span>
            <span className="font-medium">{employee.start_date}</span>
          </div>
          <div>
            <span className="text-gray-500">Total Findings: </span>
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
              Highest: {employee.highest_severity.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      <h2 className="text-xl font-semibold mt-8 mb-4">Reports</h2>

      <div className="grid gap-3">
        {reports.map((r) => (
          <Link
            key={r.id}
            to={`/reports/${r.id}`}
            className="block bg-white rounded-lg border border-gray-200 p-4 hover:border-gray-400 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">
                  Clip: {r.clip_id || "N/A"}
                </p>
                <p className="text-sm text-gray-500">
                  {r.created_at
                    ? new Date(r.created_at).toLocaleString()
                    : "No date"}
                </p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="text-right">
                  <p className="text-gray-500">Findings</p>
                  <p className="font-medium">{r.total_findings}</p>
                </div>
                <div className="text-right text-xs text-gray-500">
                  {r.code_backed_count > 0 && (
                    <p>{r.code_backed_count} health</p>
                  )}
                  {r.guidance_count > 0 && <p>{r.guidance_count} guidance</p>}
                  {r.efficiency_count > 0 && (
                    <p>{r.efficiency_count} efficiency</p>
                  )}
                </div>
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-medium ${SEVERITY_COLORS[r.highest_severity] || SEVERITY_COLORS.low}`}
                >
                  {r.highest_severity.toUpperCase()}
                </span>
              </div>
            </div>
          </Link>
        ))}

        {reports.length === 0 && (
          <p className="text-gray-500">No reports for this employee.</p>
        )}
      </div>
    </div>
  );
}
