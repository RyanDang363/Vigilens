import { useEffect, useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchEmployees,
  fetchAllFindings,
  type Employee,
  type FindingWithEmployee,
} from "../lib/api";

// ─── Color maps ─────────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, string> = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-orange-50 text-orange-700 border-orange-200",
  critical: "bg-red-50 text-red-700 border-red-200",
};

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

type ViewMode = "employees" | "offenses" | "positions";
type SortDir = "asc" | "desc";
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

// ─── Offense card (grouped finding type) ────────────────────────────
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
        className="w-full text-left p-5 flex items-center justify-between cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">
            {CLASS_ICON[group.findingClass] || "📋"}
          </span>
          <div>
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

        <div className="flex items-center gap-4 text-sm">
          <div className="text-right">
            <p className="text-xs text-gray-400 uppercase tracking-wide">Occurrences</p>
            <p className="text-xl font-bold text-gray-900">{group.totalCount}</p>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${
              SEVERITY_PILL[group.highestSeverity] || SEVERITY_PILL.low
            }`}
          >
            {group.highestSeverity.toUpperCase()}
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform duration-300 ${
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
                <div className="flex items-center gap-1.5">
                  <div className="w-12 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        f.evidence_confidence >= 0.8
                          ? "bg-emerald-500"
                          : f.evidence_confidence >= 0.6
                          ? "bg-amber-500"
                          : "bg-red-400"
                      }`}
                      style={{ width: `${f.evidence_confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-gray-400 text-xs">
                    {(f.evidence_confidence * 100).toFixed(0)}%
                  </span>
                </div>
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

          {/* Expanded detail: reasoning summary */}
          <div className="px-5 py-4 bg-gradient-to-r from-gray-50 to-blue-50/30 text-sm text-gray-600">
            <p className="font-semibold text-gray-700 mb-1.5 flex items-center gap-1.5">
              <span className="text-base">💡</span> Example reasoning:
            </p>
            <p className="italic leading-relaxed">{group.findings[0]?.reasoning}</p>
            {group.findings[0]?.training_recommendation && (
              <div className="mt-3 p-3 bg-white/70 rounded-lg border border-blue-100">
                <span className="font-semibold text-blue-700">Coaching: </span>
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
  const [minFindings, setMinFindings] = useState(0);
  const [selectedRole, setSelectedRole] = useState<string>("all");
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Offense filters
  const [offenseClassFilter, setOffenseClassFilter] = useState<OffenseClassFilter>("all");

  useEffect(() => {
    Promise.all([fetchEmployees(), fetchAllFindings()])
      .then(([emps, fndgs]) => {
        setEmployees(emps);
        setFindings(fndgs);
      })
      .finally(() => setLoading(false));
  }, []);

  // Unique roles
  const roles = useMemo(() => {
    const roleSet = new Set(employees.map((e) => e.role).filter(Boolean));
    return Array.from(roleSet).sort();
  }, [employees]);

  // Available offense classes
  const offenseClasses = useMemo(() => {
    const set = new Set(findings.map((f) => f.finding_class));
    return Array.from(set).sort();
  }, [findings]);

  // Filtered & sorted employees
  const filteredEmployees = useMemo(() => {
    const filtered = employees.filter((emp) => {
      if (emp.total_findings < minFindings) return false;
      if (selectedRole !== "all" && emp.role !== selectedRole) return false;
      return true;
    });

    filtered.sort((a, b) => {
      let cmp = 0;
      if (sortField === "name") {
        cmp = a.name.localeCompare(b.name);
      } else if (sortField === "findings") {
        cmp = a.total_findings - b.total_findings;
      } else if (sortField === "severity") {
        cmp = (SEV_ORDER[a.highest_severity] || 0) - (SEV_ORDER[b.highest_severity] || 0);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return filtered;
  }, [employees, minFindings, selectedRole, sortField, sortDir]);

  // Grouped offenses with class filter
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
          label="Total Findings"
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
          {viewMode === "offenses" && "Offenses"}
          {viewMode === "positions" && "By Position"}
        </h1>
      </div>

      {/* ─── View mode tabs ───────────────────────────── */}
      <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-gray-200/60 p-3 mb-6">
        <div className="flex flex-wrap items-center gap-2">
          {(
            [
              ["employees", "By Employee", "👤"],
              ["offenses", "By Offense", "🚨"],
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

          <div className="h-6 w-px bg-gray-200 mx-1" />

          {/* ─── Employee view filters ─── */}
          {viewMode === "employees" && (
            <>
              <select
                value={minFindings}
                onChange={(e) => setMinFindings(Number(e.target.value))}
                className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
              >
                <option value={0}>All Findings</option>
                <option value={1}>1+ Findings</option>
                <option value={2}>2+ Findings</option>
                <option value={3}>3+ Findings</option>
                <option value={5}>5+ Findings</option>
              </select>

              {roles.length > 1 && (
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
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
                className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
              >
                <option value="name">Sort: Name</option>
                <option value="findings">Sort: Findings</option>
                <option value="severity">Sort: Severity</option>
              </select>

              <button
                onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                className="flex items-center gap-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 cursor-pointer transition-colors"
                title={sortDir === "asc" ? "Ascending" : "Descending"}
              >
                <svg
                  className={`w-4 h-4 text-gray-600 transition-transform duration-200 ${
                    sortDir === "desc" ? "rotate-180" : ""
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                </svg>
                <span className="text-gray-600">{sortDir === "asc" ? "A→Z" : "Z→A"}</span>
              </button>
            </>
          )}

          {/* ─── Offense view filters ─── */}
          {viewMode === "offenses" && (
            <>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setOffenseClassFilter("all")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                    offenseClassFilter === "all"
                      ? "bg-gray-800 text-white shadow-sm"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  All Types
                </button>
                {offenseClasses.map((cls) => (
                  <button
                    key={cls}
                    onClick={() => setOffenseClassFilter(cls as OffenseClassFilter)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all flex items-center gap-1 ${
                      offenseClassFilter === cls
                        ? "bg-gray-800 text-white shadow-sm"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    <span>{CLASS_ICON[cls] || "📋"}</span>
                    {CLASS_LABEL[cls] || cls}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* ─── Position view filters ─── */}
          {viewMode === "positions" && (
            <>
              <select
                value={minFindings}
                onChange={(e) => setMinFindings(Number(e.target.value))}
                className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow"
              >
                <option value={0}>All Findings</option>
                <option value={1}>1+ Findings</option>
                <option value={2}>2+ Findings</option>
                <option value={3}>3+ Findings</option>
              </select>
            </>
          )}
        </div>
      </div>

      {/* ─── BY EMPLOYEE view ─────────────────────────── */}
      {viewMode === "employees" && (
        <div className="grid gap-3">
          {filteredEmployees.map((emp) => (
            <Link
              key={emp.id}
              to={`/employees/${emp.id}`}
              className={`block bg-white rounded-xl border border-gray-200 p-5 card-lift severity-accent-${emp.total_findings > 0 ? emp.highest_severity : "low"}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-100 to-violet-100 flex items-center justify-center text-sm font-bold text-blue-700 shrink-0">
                    {emp.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">
                      {emp.name}
                    </h2>
                    <p className="text-sm text-gray-400">
                      {emp.role}
                      {emp.station && ` · ${emp.station}`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-5 text-sm">
                  <div className="text-center">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Findings</p>
                    <p className={`text-lg font-bold ${emp.total_findings > 0 ? "text-gray-900" : "text-gray-300"}`}>
                      {emp.total_findings}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Reports</p>
                    <p className={`text-lg font-bold ${emp.total_reports > 0 ? "text-gray-900" : "text-gray-300"}`}>
                      {emp.total_reports}
                    </p>
                  </div>
                  {emp.total_findings > 0 && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        SEVERITY_PILL[emp.highest_severity] ||
                        SEVERITY_PILL.low
                      }`}
                    >
                      {emp.highest_severity.toUpperCase()}
                    </span>
                  )}
                  <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Link>
          ))}

          {filteredEmployees.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">No employees match the current filters.</p>
              <button
                onClick={() => {
                  setMinFindings(0);
                  setSelectedRole("all");
                }}
                className="mt-3 text-sm text-blue-600 hover:underline cursor-pointer"
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* ─── BY OFFENSE view ──────────────────────────── */}
      {viewMode === "offenses" && (
        <div className="grid gap-3">
          {offenseGroups.map((group) => (
            <OffenseCard key={group.concludedType} group={group} />
          ))}

          {offenseGroups.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">No offenses match the selected type.</p>
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
                  <Link
                    key={emp.id}
                    to={`/employees/${emp.id}`}
                    className={`block bg-white rounded-xl border border-gray-200 p-4 card-lift severity-accent-${emp.total_findings > 0 ? emp.highest_severity : "low"}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-100 to-violet-100 flex items-center justify-center text-xs font-bold text-blue-700">
                          {emp.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">
                            {emp.name}
                          </h3>
                          <p className="text-xs text-gray-400">
                            {emp.station || "No station"}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="text-center">
                          <p className="text-xs text-gray-400 uppercase tracking-wide">
                            Findings
                          </p>
                          <p className="font-bold">{emp.total_findings}</p>
                        </div>
                        {emp.total_findings > 0 && (
                          <span
                            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                              SEVERITY_PILL[emp.highest_severity] ||
                              SEVERITY_PILL.low
                            }`}
                          >
                            {emp.highest_severity.toUpperCase()}
                          </span>
                        )}
                        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </Link>
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
    </div>
  );
}
