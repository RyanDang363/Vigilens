import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchEmployees, type Employee } from "../lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-700",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export default function Roster() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEmployees()
      .then(setEmployees)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Employee Roster</h1>

      <div className="grid gap-4">
        {employees.map((emp) => (
          <Link
            key={emp.id}
            to={`/employees/${emp.id}`}
            className="block bg-white rounded-lg border border-gray-200 p-5 hover:border-gray-400 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-medium text-gray-900">
                  {emp.name}
                </h2>
                <p className="text-sm text-gray-500">
                  {emp.role}
                  {emp.station && ` — ${emp.station}`}
                </p>
              </div>

              <div className="flex items-center gap-4 text-sm">
                <div className="text-right">
                  <p className="text-gray-500">Findings</p>
                  <p className="font-medium text-gray-900">
                    {emp.total_findings}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-gray-500">Reports</p>
                  <p className="font-medium text-gray-900">
                    {emp.total_reports}
                  </p>
                </div>
                {emp.total_findings > 0 && (
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ${SEVERITY_COLORS[emp.highest_severity] || SEVERITY_COLORS.low}`}
                  >
                    {emp.highest_severity.toUpperCase()}
                  </span>
                )}
              </div>
            </div>
          </Link>
        ))}

        {employees.length === 0 && (
          <p className="text-gray-500">No employees found.</p>
        )}
      </div>
    </div>
  );
}
