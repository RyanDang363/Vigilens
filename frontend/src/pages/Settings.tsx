import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  fetchGoogleStatus,
  getGoogleLoginUrl,
  createGoogleSheet,
  type GoogleStatus,
} from "../lib/api";

export default function Settings() {
  const [searchParams] = useSearchParams();
  const [google, setGoogle] = useState<GoogleStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState("");

  const justConnected = searchParams.get("google") === "connected";

  useEffect(() => {
    fetchGoogleStatus()
      .then(setGoogle)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (justConnected) {
      setMessage("Google account connected successfully!");
      fetchGoogleStatus().then(setGoogle);
    }
  }, [justConnected]);

  const handleConnect = async () => {
    setActionLoading(true);
    try {
      const url = await getGoogleLoginUrl();
      window.location.href = url;
    } catch {
      setMessage("Failed to start Google login.");
      setActionLoading(false);
    }
  };

  const handleCreateSheet = async () => {
    setActionLoading(true);
    setMessage("");
    try {
      const result = await createGoogleSheet();
      setGoogle((prev) =>
        prev
          ? { ...prev, sheet_id: result.sheet_id, sheet_url: result.sheet_url }
          : prev
      );
      setMessage("New spreadsheet created!");
    } catch {
      setMessage("Failed to create spreadsheet.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      {message && (
        <div className="mb-6 p-4 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 text-sm">
          {message}
        </div>
      )}

      {/* Google Integration */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">
          Google Integration
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Connect your Google account to automatically log infractions to a Google
          Sheet.
        </p>

        {google?.connected ? (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-green-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Connected</p>
                <p className="text-sm text-gray-500">{google.email}</p>
              </div>
            </div>

            {google.sheet_url ? (
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="text-sm font-medium text-gray-700 mb-1">
                  Vigilens Infractions Sheet
                </p>
                <a
                  href={google.sheet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline break-all"
                >
                  {google.sheet_url}
                </a>
              </div>
            ) : (
              <p className="text-sm text-gray-500 mb-4">
                No spreadsheet created yet.
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleCreateSheet}
                disabled={actionLoading}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 cursor-pointer transition-colors"
              >
                {google.sheet_url
                  ? "Create New Sheet"
                  : "Create Infractions Sheet"}
              </button>
              <button
                onClick={handleConnect}
                disabled={actionLoading}
                className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50 cursor-pointer transition-colors"
              >
                Reconnect Account
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={handleConnect}
            disabled={actionLoading}
            className="flex items-center gap-3 px-5 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors disabled:opacity-50"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            <span className="font-medium text-gray-700">
              Connect Google Account
            </span>
          </button>
        )}
      </div>
    </div>
  );
}
