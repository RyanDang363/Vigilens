import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  fetchTrainingSources,
  fetchTrainingSource,
  getApiErrorMessage,
  getTrainingSourceFileUrl,
  uploadTrainingFile,
  type TrainingSource,
  type TrainingSourceSummary,
} from "../lib/api";

function formatSourceType(sourceType: string) {
  return sourceType === "google_doc" ? "Google Doc" : "Upload";
}

function canPreviewInline(source: TrainingSource | null): boolean {
  if (!source) return false;
  return source.source_type === "upload";
}

function viewerHeight(mimeType: string): string {
  return mimeType === "application/pdf" ? "h-[760px]" : "h-[420px]";
}

export default function TrainingLibrary() {
  const [sources, setSources] = useState<TrainingSourceSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedSource, setSelectedSource] = useState<TrainingSource | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyLabel, setBusyLabel] = useState("");
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState<"success" | "error" | "neutral">("neutral");
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  async function refreshSources(preferredSourceId?: string) {
    const all = await fetchTrainingSources();
    setSources(all);
    const nextId = preferredSourceId ?? selectedId ?? "";
    const resolvedId = nextId && all.some((item) => item.id === nextId) ? nextId : "";
    setSelectedId(resolvedId);
    if (resolvedId) {
      const detail = await fetchTrainingSource(resolvedId);
      setSelectedSource(detail);
    } else {
      setSelectedSource(null);
    }
  }

  useEffect(() => {
    refreshSources()
      .catch((error: unknown) => {
        setMessage(getApiErrorMessage(error) || "Could not load uploaded files.");
        setMessageTone("error");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetchTrainingSource(selectedId)
      .then(setSelectedSource)
      .catch((error: unknown) => {
        setMessage(getApiErrorMessage(error) || "Could not load the selected file.");
        setMessageTone("error");
      });
  }, [selectedId]);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setBusyLabel(`Uploading ${file.name}...`);
      setMessage("");
      const source = await uploadTrainingFile(file);
      await refreshSources(source.id);
      setMessage(`${file.name} uploaded successfully. Click any file on the left to view it here.`);
      setMessageTone("success");
    } catch (error) {
      setMessage(getApiErrorMessage(error) || "Upload failed.");
      setMessageTone("error");
    } finally {
      setBusyLabel("");
      event.target.value = "";
    }
  }

  if (loading) {
    return <p className="text-slate-500">Loading uploaded files...</p>;
  }

  const fileUrl = selectedSource ? getTrainingSourceFileUrl(selectedSource.id) : "";

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-slate-200 bg-[radial-gradient(circle_at_top_left,#fff6dc,transparent_32%),linear-gradient(135deg,#f8fbff_0%,#fffdf7_50%,#eef8f3_100%)] p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
              File Viewer
            </p>
            <h1 className="mt-3 font-serif text-4xl text-slate-900">
              Upload files and view them directly inside the page.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
              This page is now just a lightweight file library. Upload a PDF or text file,
              then click it from the list to open it in the in-page viewer on the right.
            </p>
          </div>

          <div className="rounded-2xl border border-white/70 bg-white/85 p-4 text-sm text-slate-600 shadow-sm">
            <p className="font-semibold text-slate-900">Uploaded files</p>
            <p className="mt-1">{sources.length} saved in this workspace</p>
          </div>
        </div>
      </section>

      {(busyLabel || message) && (
        <section
          className={`rounded-2xl border px-5 py-4 shadow-sm ${
            messageTone === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : messageTone === "error"
                ? "border-rose-200 bg-rose-50 text-rose-900"
                : "border-amber-200 bg-amber-50 text-amber-900"
          }`}
        >
          {busyLabel && <p className="text-sm font-medium">{busyLabel}</p>}
          {message && <p className={`text-sm ${busyLabel ? "mt-1" : ""}`}>{message}</p>}
        </section>
      )}

      <section className="grid gap-6">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Upload
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-900">Add a file</h2>
            </div>
          </div>

          <input
            ref={uploadInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.txt,.md,.docx"
            onChange={handleUpload}
          />

          <button
            type="button"
            onClick={() => uploadInputRef.current?.click()}
            className="mt-5 w-full rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-4 text-left transition hover:border-slate-400 hover:bg-slate-100"
          >
            <p className="text-sm font-semibold text-slate-900">Upload file</p>
            <p className="mt-1 text-xs text-slate-500">PDF, TXT, MD, or DOCX</p>
          </button>
        </div>

        <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Uploaded Files
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-900">Library</h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
              {sources.length}
            </span>
          </div>

          <div className="mt-5 grid gap-4">
              {sources.map((source) => (
                <div key={source.id} className="rounded-2xl border border-slate-200 bg-slate-50">
                  <button
                    type="button"
                    onClick={() => setSelectedId((current) => (current === source.id ? "" : source.id))}
                    className={`w-full rounded-2xl p-4 text-left transition ${
                      selectedId === source.id
                        ? "bg-slate-900 text-white shadow-sm"
                        : "text-slate-700 hover:bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="font-medium">{source.title}</p>
                        <p
                          className={`mt-1 text-xs ${
                            selectedId === source.id ? "text-slate-300" : "text-slate-500"
                          }`}
                        >
                          {formatSourceType(source.source_type)} • {source.mime_type}
                        </p>
                      </div>
                      <span
                        className={`text-xs font-medium ${
                          selectedId === source.id ? "text-slate-300" : "text-slate-500"
                        }`}
                      >
                        {selectedId === source.id ? "Hide viewer" : "View in page"}
                      </span>
                    </div>
                  </button>

                  {selectedId === source.id && selectedSource?.id === source.id && (
                    <div className="border-t border-slate-200 bg-white p-4">
                      <div className="mb-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                          In-Page Viewer
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          {formatSourceType(selectedSource.source_type)} • {selectedSource.mime_type}
                        </p>
                      </div>

                      {canPreviewInline(selectedSource) ? (
                        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                          <iframe
                            title={`${selectedSource.title} preview`}
                            src={fileUrl}
                            className={`w-full bg-white ${viewerHeight(selectedSource.mime_type)}`}
                          />
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                          This file type does not support inline preview yet.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {sources.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 p-5 text-sm text-slate-500">
                  No files yet. Upload one and it will appear here.
                </div>
              )}
            </div>
        </section>
      </section>
    </div>
  );
}
