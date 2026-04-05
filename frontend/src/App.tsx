import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { LayoutDashboard, BookOpen, Settings as SettingsIcon } from "lucide-react";
import Roster from "./pages/Roster";
import EmployeeDetail from "./pages/EmployeeDetail";
import ReportDetail from "./pages/ReportDetail";
import TrainingLibrary from "./pages/TrainingLibrary";
import Settings from "./pages/Settings";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p === "/" },
  { to: "/training", label: "Training", icon: BookOpen, match: (p: string) => p.startsWith("/training") },
  { to: "/settings", label: "Settings", icon: SettingsIcon, match: (p: string) => p.startsWith("/settings") },
];

function NavBar() {
  const { pathname } = useLocation();

  return (
    <nav className="sticky top-0 z-50 glass border-b border-white/30">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center gap-8">
        <Link
          to="/"
          className="flex items-center gap-3 shrink-0 group"
          aria-label="Vigilens home"
        >
          <img
            src="/vigilens-mark.png"
            alt=""
            width={246}
            height={182}
            className="size-9 shrink-0 rounded-xl object-contain bg-indigo-50 p-0.5 ring-1 ring-indigo-100 group-hover:ring-indigo-200 transition-all"
            draggable={false}
          />
          <span className="text-lg font-extrabold uppercase tracking-[0.12em] text-gray-900 group-hover:text-indigo-700 transition-colors">
            Vigilens
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, match }) => {
            const active = match(pathname);
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100/60"
                }`}
              >
                <Icon className="w-4 h-4" strokeWidth={active ? 2.5 : 2} />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <NavBar />
        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Roster />} />
            <Route path="/training" element={<TrainingLibrary />} />
            <Route path="/employees/:id" element={<EmployeeDetail />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
