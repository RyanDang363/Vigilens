import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Roster from "./pages/Roster";
import EmployeeDetail from "./pages/EmployeeDetail";
import ReportDetail from "./pages/ReportDetail";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200/60 px-6 py-4 sticky top-0 z-50">
          <div className="max-w-6xl mx-auto flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
                <svg className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <span className="text-xl font-bold gradient-text">
                SafeWatch
              </span>
            </Link>
            <Link
              to="/"
              className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              Dashboard
            </Link>
          </div>
        </nav>

        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Roster />} />
            <Route path="/employees/:id" element={<EmployeeDetail />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
