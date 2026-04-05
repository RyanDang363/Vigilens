import { useEffect, useState, useMemo, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  createEmployee,
  fetchEmployees,
  fetchAllFindings,
  getApiErrorMessage,
  type Employee,
  type FindingWithEmployee,
} from "../lib/api";
import { normalizeObservationGrammar } from "../lib/reasoning";

// ─── Color maps ─────────────────────────────────────────────────────
const SEVERITY_PILL: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const SEVERITY_DOT: Record<string, string> = {
  low: "bg-emerald-400",
  medium: "bg-amber-400",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

const CLASS_BADGE: Record<string, string> = {
  code_backed_food_safety: "bg-blue-100 text-blue-700 border border-blue-200",
  workplace_safety_rule: "bg-violet-100 text-violet-700 border border-violet-200",
  efficiency: "bg-cyan-100 text-cyan-700 border border-cyan-200",
  house_rule: "bg-gray-100 text-gray-600 border border-gray-200",
};

const CLASS_LABEL: Record<string, string> = {
  code_backed_food_safety: "Health Code",
  workplace_safety_rule: "Workplace Safety",
  efficiency: "Efficiency",
  house_rule: "House Rule",
};

const CLASS_ICON: Record<string, string> = {
  code_backed_food_safety: "🏥",
  workplace_safety_rule: "⚠️",
  efficiency: "⚡",
  house_rule: "🏠",
};

/** Native <select> uses OS chrome (inset / gradient) unless appearance is reset. */
const ROSTER_SELECT_CLASS =
  "text-sm min-h-[2.5rem] cursor-pointer rounded-lg border border-gray-200 bg-white pl-3 pr-9 py-2 shadow-none " +
  "transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 " +
  "appearance-none bg-[length:1rem] bg-[position:right_0.625rem_center] bg-no-repeat " +
  "bg-[url('data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%222%22%3E%3Cpath%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20d%3D%22M6%209l6%206%206-6%22%2F%3E%3C%2Fsvg%3E')]";

type ViewMode = "employees" | "offenses" | "positions";
type SortField = "name" | "findings" | "severity";
type OffenseClassFilter = "all" | "code_backed_food_safety" | "workplace_safety_rule" | "efficiency" | "house_rule";

function formatType(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const SEV_ORDER: Record<string, number> = { low: 0, medium: 1, high: 2, critical: 3 };

// ─── Stat card ──────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: string;
  color: string;
}) {
  return (
    <div className={`rounded-xl p-4 ${color} border`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-medium uppercase tracking-wide opacity-70">
          {label}
        </span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

// ─── Infraction-type card (grouped by concluded_type) ───────────────
interface OffenseGroup {
  concludedType: string;
  findingClass: string;
  highestSeverity: string;
  totalCount: number;
  findings: FindingWithEmployee[];
}

function OffenseCard({ group }: { group: OffenseGroup }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 overflow-hidden card-lift severity-accent-${group.highestSeverity}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-5 grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6 cursor-pointer"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-2xl shrink-0">
            {CLASS_ICON[group.findingClass] || "📋"}
          </span>
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-gray-900">
              {formatType(group.concludedType)}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  CLASS_BADGE[group.findingClass] || CLASS_BADGE.house_rule
                }`}
              >
                {CLASS_LABEL[group.findingClass] || group.findingClass}
              </span>
            </div>
          </div>
        </div>

        {/* Fixed columns so Occurrences + severity + chevron line up across every card */}
        <div className="grid grid-cols-[5.75rem_7.5rem_1.5rem] items-center gap-3 text-sm sm:justify-self-end shrink-0">
          <div className="text-center w-full">
            <p className="text-xs text-gray-400 uppercase tracking-wide leading-tight">
              Occurrences
            </p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{group.totalCount}</p>
          </div>
          <div className="flex justify-center w-full">
            <span
              className={`inline-flex justify-center px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                SEVERITY_PILL[group.highestSeverity] || SEVERITY_PILL.low
              }`}
            >
              {group.highestSeverity.toUpperCase()}
            </span>
          </div>
          <div className="flex justify-center">
            <svg
              className={`w-5 h-5 text-gray-400 transition-transform duration-300 shrink-0 ${
                expanded ? "rotate-180" : ""
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 expand-content">
          {group.findings.map((f, i) => (
            <Link
              key={f.id}
              to={`/reports/${f.report_id}`}
              className={`flex items-center justify-between px-5 py-3.5 hover:bg-blue-50/50 transition-colors ${
                i < group.findings.length - 1 ? "border-b border-gray-100" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-violet-100 flex items-center justify-center text-xs font-semibold text-blue-700">
                  {f.employee_name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{f.employee_name}</p>
                  <p className="text-xs text-gray-400">{f.employee_role}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-gray-400 text-xs font-mono">
                  {f.timestamp_start} – {f.timestamp_end}
                </span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    SEVERITY_DOT[f.severity] || SEVERITY_DOT.low
                  }`}
                />
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    SEVERITY_PILL[f.severity] || SEVERITY_PILL.low
                  }`}
                >
                  {f.severity.toUpperCase()}
                </span>
              </div>
            </Link>
          ))}

          <div className="px-5 py-4 bg-gradient-to-r from-gray-50 to-blue-50/30 text-sm text-gray-600">
            <p className="font-semibold text-gray-700 mb-1.5 flex items-center gap-1.5">
              <span className="text-base">💡</span> Infraction recorded:
            </p>
            <p className="italic leading-relaxed">
              {group.findings[0]?.reasoning
                ? normalizeObservationGrammar(group.findings[0].reasoning)
                : null}
            </p>
            {group.findings[0]?.training_recommendation && (
              <div className="mt-3 p-3 bg-white/70 rounded-lg border border-blue-100">
                <span className="font-semibold text-blue-700">Mitigation: </span>
                <span className="text-gray-700">{group.findings[0].training_recommendation}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Roster component ──────────────────────────────────────────
export default function Roster() {
  const [searchParams] = useSearchParams();
  const initialView = (searchParams.get("view") as ViewMode) || "employees";

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [findings, setFindings] = useState<FindingWithEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);

  // Employee filters
  const [selectedRole, setSelectedRole] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("name");

  // Infraction-type filters (by finding_class)
  const [offenseClassFilter, setOffenseClassFilter] = useState<OffenseClassFilter>("all");

  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    id: "",
    name: "",
    email: "",
    role: "",
    station: "",
    start_date: "",
  });
  const [addSaving, setAddSaving] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const refetchRoster = async () => {
    const [emps, fndgs] = await Promise.all([fetchEmployees(), fetchAllFindings()]);
    setEmployees(emps);
    setFindings(fndgs);
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    refetchRoster()
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const openAddModal = () => {
    setAddForm({ id: "", name: "", email: "", role: "", station: "", start_date: "" });
    setAddError(null);
    setAddOpen(true);
  };

  const submitAddEmployee = async (e: FormEvent) => {
    e.preventDefault();
    if (!addForm.id.trim() || !addForm.name.trim()) {
      setAddError("Employee ID and name are required.");
      return;
    }
    setAddSaving(true);
    setAddError(null);
    try {
      await createEmployee(addForm);
      setAddOpen(false);
      await refetchRoster();
    } catch (err) {
      setAddError(getApiErrorMessage(err));
    } finally {
      setAddSaving(false);
    }
  };

  // Unique roles
  const roles = useMemo(() => {
    const roleSet = new Set(employees.map((e) => e.role).filter(Boolean));
    return Array.from(roleSet).sort();
  }, [employees]);

  // Available infraction classes
  const offenseClasses = useMemo(() => {
    const set = new Set(findings.map((f) => f.finding_class));
    return Array.from(set).sort();
  }, [findings]);

  // Filtered & sorted employees
  const filteredEmployees = useMemo(() => {
    const filtered = employees.filter((emp) => {
      if (selectedRole !== "all" && emp.role !== selectedRole) return false;
      return true;
    });

    filtered.sort((a, b) => {
      let cmp = 0;
      if (sortField === "name") {
        cmp = a.name.localeCompare(b.name);
        return cmp;
      }
      if (sortField === "findings") {
        cmp = a.total_findings - b.total_findings;
        return -cmp;
      }
      cmp =
        (SEV_ORDER[a.highest_severity] || 0) - (SEV_ORDER[b.highest_severity] || 0);
      return -cmp;
    });

    return filtered;
  }, [employees, selectedRole, sortField]);

  // Grouped infractions with class filter
  const offenseGroups = useMemo(() => {
    const relevantFindings =
      offenseClassFilter === "all"
        ? findings
        : findings.filter((f) => f.finding_class === offenseClassFilter);

    const map: Record<string, OffenseGroup> = {};
    for (const f of relevantFindings) {
      if (!map[f.concluded_type]) {
        map[f.concluded_type] = {
          concludedType: f.concluded_type,
          findingClass: f.finding_class,
          highestSeverity: f.severity,
          totalCount: 0,
          findings: [],
        };
      }
      const g = map[f.concluded_type];
      g.totalCount++;
      g.findings.push(f);
      if ((SEV_ORDER[f.severity] || 0) > (SEV_ORDER[g.highestSeverity] || 0)) {
        g.highestSeverity = f.severity;
      }
    }
    return Object.values(map).sort(
      (a, b) =>
        (SEV_ORDER[b.highestSeverity] || 0) - (SEV_ORDER[a.highestSeverity] || 0)
    );
  }, [findings, offenseClassFilter]);

  // Positions grouping
  const positionGroups = useMemo(() => {
    const map: Record<string, Employee[]> = {};
    for (const emp of filteredEmployees) {
      const r = emp.role || "Unassigned";
      if (!map[r]) map[r] = [];
      map[r].push(emp);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredEmployees]);

  // Summary stats
  const stats = useMemo(() => {
    const criticalCount = findings.filter((f) => f.severity === "critical").length;
    const highCount = findings.filter((f) => f.severity === "high").length;
    return {
      totalEmployees: employees.length,
      totalFindings: findings.length,
      criticalCount,
      highCount,
    };
  }, [employees, findings]);

  if (loading)
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );

  return (
    <div>
      {/* ─── Stats bar ────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Employees"
          value={stats.totalEmployees}
          icon="👥"
          color="bg-blue-50 text-blue-700 border-blue-200"
        />
        <StatCard
          label="Total Infractions"
          value={stats.totalFindings}
          icon="📋"
          color="bg-violet-50 text-violet-700 border-violet-200"
        />
        <StatCard
          label="Critical"
          value={stats.criticalCount}
          icon="🔴"
          color="bg-red-50 text-red-700 border-red-200"
        />
        <StatCard
          label="High Severity"
          value={stats.highCount}
          icon="🟠"
          color="bg-orange-50 text-orange-700 border-orange-200"
        />
      </div>

      {/* ─── Header ───────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {viewMode === "employees" && "Employee Roster"}
          {viewMode === "offenses" && "Infractions"}
          {viewMode === "positions" && "By Position"}
        </h1>
      </div>

      {/* ─── View mode tabs ───────────────────────────── */}
      <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-gray-200/60 p-3 mb-2">
        <div className="flex flex-wrap items-center gap-2">
          {(
            [
              ["employees", "By Employee", "👤"],
              ["offenses", "By Infraction", "🚨"],
              ["positions", "By Position", "🏷️"],
            ] as [ViewMode, string, string][]
          ).map(([mode, label, icon]) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer flex items-center gap-2 ${
                viewMode === mode
                  ? "bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-md shadow-blue-200"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Filters row (below tabs) ────────────────── */}
      {viewMode === "employees" && (
        <div className="bg-white/40 rounded-xl border border-gray-200/40 p-3 mb-6">
          <div className="flex flex-wrap items-center gap-2">
            {roles.length > 1 && (
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className={ROSTER_SELECT_CLASS}
              >
                <option value="all">All Roles</option>
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            )}

            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value as SortField)}
              className={ROSTER_SELECT_CLASS}
            >
              <option value="name">Sort: Name</option>
              <option value="findings">Sort: Infractions</option>
              <option value="severity">Sort: Severity</option>
            </select>

            <button
              type="button"
              onClick={openAddModal}
              className="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-md shadow-blue-200 hover:opacity-95 transition-opacity cursor-pointer"
            >
              + Add employee
            </button>
          </div>
        </div>
      )}

      {viewMode === "offenses" && (
        <div className="bg-white/40 rounded-xl border border-gray-200/40 p-3 mb-6">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={offenseClassFilter}
              onChange={(e) => setOffenseClassFilter(e.target.value as OffenseClassFilter)}
              className={ROSTER_SELECT_CLASS}
            >
              <option value="all">All Types</option>
              {offenseClasses.map((cls) => (
                <option key={cls} value={cls}>
                  {CLASS_LABEL[cls] || cls}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {viewMode === "positions" && <div className="mb-6" />}

      {/* ─── BY EMPLOYEE view ─────────────────────────── */}
      {viewMode === "employees" && (
        <div className="grid gap-3">
          {filteredEmployees.map((emp) => (
            <div
              key={emp.id}
              className={`flex flex-col sm:flex-row sm:items-stretch gap-2 sm:gap-0 bg-white rounded-xl border border-gray-200 overflow-hidden card-lift severity-accent-${emp.total_findings > 0 ? emp.highest_severity : "low"}`}
            >
              <Link
                to={`/employees/${emp.id}`}
                className="flex-1 flex items-center justify-between p-5 min-w-0 hover:bg-gray-50/80 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-100 to-violet-100 flex items-center justify-center text-sm font-bold text-blue-700 shrink-0">
                    {emp.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-gray-900 truncate">
                      {emp.name}
                    </h2>
                    <p className="text-sm text-gray-400 truncate">
                      {emp.role}
                      {emp.station && ` · ${emp.station}`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center text-sm shrink-0 gap-1 sm:gap-0">
                  <div className="w-[7.25rem] sm:w-28 text-center flex flex-col items-center">
                    <div className="min-h-[2.25rem] w-full flex items-end justify-center px-0.5">
                      <p className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wide leading-[1.15] text-center">
                        <span className="block">Total</span>
                        <span className="block">infractions</span>
                      </p>
                    </div>
                    <p
                      className={`text-lg font-bold tabular-nums ${emp.total_findings > 0 ? "text-gray-900" : "text-gray-300"}`}
                    >
                      {emp.total_findings}
                    </p>
                  </div>
                  <div className="w-[7.25rem] sm:w-28 text-center flex flex-col items-center">
                    <div className="min-h-[2.25rem] w-full flex items-end justify-center px-0.5">
                      <p className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wide leading-[1.15] text-center">
                        <span className="block">Total</span>
                        <span className="block">reports</span>
                      </p>
                    </div>
                    <p
                      className={`text-lg font-bold tabular-nums ${emp.total_reports > 0 ? "text-gray-900" : "text-gray-300"}`}
                    >
                      {emp.total_reports}
                    </p>
                  </div>
                  <div className="w-[4.5rem] sm:w-20 flex flex-col items-center shrink-0">
                    <div className="min-h-[2.25rem] w-full" aria-hidden />
                    <div className="min-h-[1.75rem] flex items-center justify-center w-full">
                      {emp.total_findings > 0 ? (
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            SEVERITY_PILL[emp.highest_severity] ||
                            SEVERITY_PILL.low
                          }`}
                        >
                          {emp.highest_severity.toUpperCase()}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <svg className="w-5 h-5 text-gray-300 ml-2 self-center" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
              <div className="flex sm:flex-col justify-center border-t sm:border-t-0 sm:border-l border-gray-100 px-3 py-2 sm:py-5 sm:pr-4 bg-gray-50/50 sm:bg-transparent">
                <Link
                  to={`/employees/${emp.id}#end-of-day-upload`}
                  className="text-center text-sm font-medium text-blue-600 hover:text-blue-800 px-3 py-2 rounded-lg hover:bg-blue-50 transition-colors whitespace-nowrap"
                >
                  Upload video
                </Link>
              </div>
            </div>
          ))}

          {filteredEmployees.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">No employees match the current filters.</p>
              <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedRole("all")}
                  className="text-sm text-blue-600 hover:underline cursor-pointer"
                >
                  Clear filters
                </button>
                <button
                  type="button"
                  onClick={openAddModal}
                  className="text-sm font-medium text-white px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-violet-600 hover:opacity-95 cursor-pointer"
                >
                  Add employee
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── BY INFRACTION view ───────────────────────── */}
      {viewMode === "offenses" && (
        <div className="grid gap-3">
          {offenseGroups.map((group) => (
            <OffenseCard key={group.concludedType} group={group} />
          ))}

          {offenseGroups.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">No infractions match the selected type.</p>
              <button
                onClick={() => setOffenseClassFilter("all")}
                className="mt-3 text-sm text-blue-600 hover:underline cursor-pointer"
              >
                Show all types
              </button>
            </div>
          )}
        </div>
      )}

      {/* ─── BY POSITION view ─────────────────────────── */}
      {viewMode === "positions" && (
        <div className="space-y-8">
          {positionGroups.map(([role, emps]) => (
            <div key={role}>
              <h2 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-gradient-to-br from-blue-500 to-violet-500" />
                {role}
                <span className="ml-1 text-sm font-normal text-gray-400">
                  ({emps.length} employee{emps.length !== 1 && "s"})
                </span>
              </h2>
              <div className="grid gap-3">
                {emps.map((emp) => (
                  <div
                    key={emp.id}
                    className={`flex flex-col sm:flex-row sm:items-stretch gap-1 sm:gap-0 bg-white rounded-xl border border-gray-200 overflow-hidden card-lift severity-accent-${emp.total_findings > 0 ? emp.highest_severity : "low"}`}
                  >
                    <Link
                      to={`/employees/${emp.id}`}
                      className="flex-1 flex items-center justify-between p-4 min-w-0 hover:bg-gray-50/80 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-100 to-violet-100 flex items-center justify-center text-xs font-bold text-blue-700 shrink-0">
                          {emp.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div className="min-w-0">
                          <h3 className="font-semibold text-gray-900 truncate">
                            {emp.name}
                          </h3>
                          <p className="text-xs text-gray-400 truncate">
                            {emp.station || "No station"}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-sm shrink-0">
                        <div className="w-[7.25rem] sm:w-28 text-center flex flex-col items-center">
                          <div className="min-h-[2.25rem] w-full flex items-end justify-center px-0.5">
                            <p className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wide leading-[1.15] text-center">
                              <span className="block">Total</span>
                              <span className="block">infractions</span>
                            </p>
                          </div>
                          <p className="font-bold tabular-nums min-h-[1.75rem] flex items-center justify-center">
                            {emp.total_findings}
                          </p>
                        </div>
                        <div className="w-[4.5rem] sm:w-20 flex flex-col items-center shrink-0">
                          <div className="min-h-[2.25rem] w-full" aria-hidden />
                          <div className="min-h-[1.75rem] flex items-center justify-center w-full">
                            {emp.total_findings > 0 ? (
                              <span
                                className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                                  SEVERITY_PILL[emp.highest_severity] ||
                                  SEVERITY_PILL.low
                                }`}
                              >
                                {emp.highest_severity.toUpperCase()}
                              </span>
                            ) : null}
                          </div>
                        </div>
                        <svg
                          className="w-4 h-4 text-gray-300 self-center shrink-0"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </Link>
                    <div className="flex sm:flex-col justify-center border-t sm:border-t-0 sm:border-l border-gray-100 px-2 py-1 sm:py-4 sm:pr-3 bg-gray-50/50 sm:bg-transparent">
                      <Link
                        to={`/employees/${emp.id}#end-of-day-upload`}
                        className="text-center text-xs sm:text-sm font-medium text-blue-600 hover:text-blue-800 px-2 py-2 rounded-lg hover:bg-blue-50"
                      >
                        Upload video
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {positionGroups.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">No employees match the current filters.</p>
            </div>
          )}
        </div>
      )}

      {addOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-employee-title"
          onClick={() => !addSaving && setAddOpen(false)}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-gray-200"
            onClick={(ev) => ev.stopPropagation()}
          >
            <h2 id="add-employee-title" className="text-lg font-bold text-gray-900 mb-4">
              Add employee
            </h2>
            <form onSubmit={submitAddEmployee} className="space-y-3">
              <div>
                <label htmlFor="emp-id" className="block text-xs font-medium text-gray-500 mb-1">
                  Employee ID
                </label>
                <input
                  id="emp-id"
                  value={addForm.id}
                  onChange={(e) => setAddForm((f) => ({ ...f, id: e.target.value }))}
                  placeholder="e.g. emp_12"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  autoComplete="off"
                  disabled={addSaving}
                />
              </div>
              <div>
                <label htmlFor="emp-name" className="block text-xs font-medium text-gray-500 mb-1">
                  Name
                </label>
                <input
                  id="emp-name"
                  value={addForm.name}
                  onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Full name"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  autoComplete="name"
                  disabled={addSaving}
                />
              </div>
              <div>
                <label htmlFor="emp-email" className="block text-xs font-medium text-gray-500 mb-1">
                  Email
                </label>
                <input
                  id="emp-email"
                  type="email"
                  value={addForm.email}
                  onChange={(e) => setAddForm((f) => ({ ...f, email: e.target.value }))}
                  placeholder="name@example.com"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  autoComplete="email"
                  disabled={addSaving}
                />
              </div>
              <div>
                <label htmlFor="emp-role" className="block text-xs font-medium text-gray-500 mb-1">
                  Role
                </label>
                <input
                  id="emp-role"
                  value={addForm.role}
                  onChange={(e) => setAddForm((f) => ({ ...f, role: e.target.value }))}
                  placeholder="e.g. Line cook"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  disabled={addSaving}
                />
              </div>
              <div>
                <label htmlFor="emp-station" className="block text-xs font-medium text-gray-500 mb-1">
                  Station
                </label>
                <input
                  id="emp-station"
                  value={addForm.station}
                  onChange={(e) => setAddForm((f) => ({ ...f, station: e.target.value }))}
                  placeholder="e.g. Grill"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  disabled={addSaving}
                />
              </div>
              <div>
                <label htmlFor="emp-start" className="block text-xs font-medium text-gray-500 mb-1">
                  Start date
                </label>
                <input
                  id="emp-start"
                  value={addForm.start_date}
                  onChange={(e) => setAddForm((f) => ({ ...f, start_date: e.target.value }))}
                  placeholder="e.g. 2026-01-15"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  disabled={addSaving}
                />
              </div>
              {addError && (
                <p className="text-sm text-red-600" role="alert">
                  {addError}
                </p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => !addSaving && setAddOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer disabled:opacity-50"
                  disabled={addSaving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addSaving}
                  className="px-4 py-2 text-sm font-medium text-white rounded-lg bg-gradient-to-r from-blue-600 to-violet-600 hover:opacity-95 cursor-pointer disabled:opacity-50"
                >
                  {addSaving ? "Saving…" : "Add"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
