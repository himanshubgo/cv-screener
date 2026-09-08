import type { HealthInfo } from "../types";

export function Header({ health }: { health: HealthInfo | null; healthError: string | null }) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          <img src="/logo.webp" alt="Bill Gosling Outsourcing" className="h-9 w-auto" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">CV Screener</h1>
            <p className="text-sm text-slate-500">
              Call-centre-agent fitness screening, scored against 7 weighted criteria.
            </p>
          </div>
        </div>
        {health && !health.has_api_key && (
          <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 ring-1 ring-inset ring-amber-600/20">
            ANTHROPIC_API_KEY is not set on the backend - screening requests will fail.
          </div>
        )}
      </div>
    </header>
  );
}
