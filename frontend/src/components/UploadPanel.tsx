import { useRef, useState, type DragEvent } from "react";

interface UploadPanelProps {
  onScreen: (files: File[]) => void;
  isScreening: boolean;
  progress: { done: number; total: number } | null;
  candidateCount: number;
  onClear: () => void;
}

export function UploadPanel({ onScreen, isScreening, progress, candidateCount, onClear }: UploadPanelProps) {
  const [pending, setPending] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | File[]) {
    const incoming = Array.from(files).filter((f) => f.name.toLowerCase().endsWith(".txt"));
    setPending((prev) => {
      const existing = new Set(prev.map((f) => `${f.name}:${f.size}`));
      const merged = [...prev];
      for (const f of incoming) {
        const key = `${f.name}:${f.size}`;
        if (!existing.has(key)) {
          merged.push(f);
          existing.add(key);
        }
      }
      return merged;
    });
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  }

  function removePending(name: string) {
    setPending((prev) => prev.filter((f) => f.name !== name));
  }

  function handleScreen() {
    if (pending.length === 0) return;
    onScreen(pending);
    setPending([]);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Import CVs</h2>
        {candidateCount > 0 && (
          <button
            onClick={onClear}
            disabled={isScreening}
            className="text-xs font-medium text-slate-500 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Clear shortlist ({candidateCount})
          </button>
        )}
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors ${
          isDragOver ? "border-indigo-400 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100"
        }`}
      >
        <p className="text-sm font-medium text-slate-700">Drop plain-text CVs here, or click to browse</p>
        <p className="mt-1 text-xs text-slate-500">.txt files only, one candidate per file</p>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,text/plain"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {pending.length > 0 && (
        <ul className="mt-3 max-h-40 space-y-1 overflow-y-auto">
          {pending.map((f) => (
            <li
              key={f.name}
              className="flex items-center justify-between rounded bg-slate-50 px-2 py-1 text-xs text-slate-600"
            >
              <span className="truncate">{f.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removePending(f.name);
                }}
                className="ml-2 shrink-0 text-slate-400 hover:text-rose-600"
                aria-label={`remove ${f.name}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={handleScreen}
        disabled={pending.length === 0 || isScreening}
        className="mt-3 w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isScreening
          ? "Screening…"
          : pending.length === 0
            ? "Screen CVs"
            : `Screen ${pending.length} CV${pending.length === 1 ? "" : "s"}`}
      </button>

      {progress && (
        <div className="mt-3">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all"
              style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {progress.done} of {progress.total} screened
          </p>
        </div>
      )}
    </div>
  );
}
