import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Roster from "./pages/Roster";
import EmployeeDetail from "./pages/EmployeeDetail";
import ReportDetail from "./pages/ReportDetail";
import TrainingLibrary from "./pages/TrainingLibrary";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <nav className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center gap-6">
            <Link to="/" className="text-xl font-semibold text-gray-900">
              SafeWatch
            </Link>
            <Link
              to="/"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Employees
            </Link>
            <Link
              to="/training"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Training
            </Link>
          </div>
        </nav>

        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Roster />} />
            <Route path="/training" element={<TrainingLibrary />} />
            <Route path="/employees/:id" element={<EmployeeDetail />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
