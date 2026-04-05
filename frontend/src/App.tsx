import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Roster from "./pages/Roster";
import EmployeeDetail from "./pages/EmployeeDetail";
import ReportDetail from "./pages/ReportDetail";
import TrainingLibrary from "./pages/TrainingLibrary";
import Settings from "./pages/Settings";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200/60 px-6 py-4 sticky top-0 z-50">
          <div className="max-w-6xl mx-auto flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link
              to="/"
              className="flex items-center gap-3 shrink-0 group min-w-0"
              aria-label="Vigilens home"
            >
              <img
                src="/vigilens-mark.png"
                alt=""
                width={246}
                height={182}
                className="size-9 shrink-0 rounded-full object-contain bg-[#E9E9F5] p-0.5 ring-1 ring-[#E9E9F5]/80 group-hover:opacity-90 transition-opacity"
                draggable={false}
              />
              <span className="text-lg font-bold uppercase tracking-[0.14em] text-[#0C0C2C] leading-none group-hover:opacity-90 transition-opacity">
                Vigilens
              </span>
            </Link>
            <Link
              to="/"
              className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              to="/training"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Training
            </Link>
            <Link
              to="/settings"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Settings
            </Link>
          </div>
        </nav>

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
