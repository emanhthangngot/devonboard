"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Loader2, Play, Award, CheckCircle2 } from "lucide-react";

type MetricRow = {
  query_id: number;
  query_text: string;
  time_to_useful_answer_ms: number;
  citations_count: number;
  evidence_count: number;
  warnings_count: number;
  evidence_usefulness_score?: number | null;
  human_quality_score?: number | null;
};

type ResultRun = {
  run_id: string;
  repo: string;
  target_branch: string;
  target_commit?: string | null;
  rows: MetricRow[];
  created_at: string;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function ResultsPage() {
  const [runs, setRuns] = useState<ResultRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<ResultRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadRuns() {
      try {
        const response = await fetch(`${backendUrl}/results/runs`);
        if (!response.ok) {
          if (active) setRuns([]);
          return;
        }
        const payload = (await response.json()) as ResultRun[];
        if (Array.isArray(payload)) {
          if (active) {
            setRuns(payload);
            setSelectedRun((current) => current || payload[0] || null);
          }
        } else {
          if (active) setRuns([]);
        }
      } catch {
        if (active) {
          setRuns([]);
          setBanner("Result API unavailable - start FastAPI before measuring app results.");
        }
      }
    }
    loadRuns();
    return () => {
      active = false;
    };
  }, []);

  async function runResults() {
    setIsRunning(true);
    setBanner(null);
    try {
      const response = await fetch(`${backendUrl}/results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo: "demo", target_branch: "dev" }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Result run failed.");
      await loadRuns();
    } catch (error) {
      setBanner(error instanceof Error ? error.message : "Result run failed.");
    } finally {
      setIsRunning(false);
    }
  }

  const rows = selectedRun?.rows || [];

  return (
    <main className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden" aria-label="Result dashboard">
      {/* Top Nav */}
      <nav className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 relative z-30" aria-label="Result status">
        <a href="/" className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">
          <ArrowLeft size={14} aria-hidden="true" />
          <span>Workspace</span>
        </a>
        <div className="flex items-center space-x-3">
          <span className="px-2 py-0.5 bg-slate-100 rounded border border-slate-250 text-xs font-semibold text-slate-600">
            DevOnboard app result
          </span>
          <button
            type="button"
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-350 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-md shadow-sm transition-colors cursor-pointer flex items-center gap-1.5"
            onClick={runResults}
            disabled={isRunning}
          >
            {isRunning ? (
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
            ) : (
              <Play size={14} aria-hidden="true" />
            )}
            <span>Run Result</span>
          </button>
        </div>
      </nav>

      {/* Banner */}
      {banner && (
        <div className="px-6 py-2 bg-rose-50 border-b border-rose-100 text-rose-950 text-xs font-medium shrink-0">
          {banner}
        </div>
      )}

      {/* Layout Grid */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Main Panel */}
        <section className="flex-1 flex flex-col bg-slate-50 overflow-y-auto p-6 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3 shrink-0">
            <div className="flex items-center gap-2">
              <BarChart3 size={20} className="text-indigo-600" aria-hidden="true" />
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">DevOnboard App Result</h1>
            </div>
            <p className="text-xs text-slate-500 leading-normal max-w-2xl">
              Measure the app retrieval output: latency, citations, evidence coverage, and warnings.
            </p>
          </div>

          {rows.length === 0 ? (
            <div className="flex-1 bg-white border border-slate-200 rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-3 shadow-sm">
              <Award className="w-10 h-10 text-slate-300" />
              <p className="text-sm text-slate-500 max-w-sm leading-normal">
                Run a result check to measure the current DevOnboard graph answer quality.
              </p>
              <button
                type="button"
                onClick={runResults}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors cursor-pointer"
              >
                Run Result
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Citation Chart */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4" aria-label="Citation count chart">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Citation count chart</h3>
                <div className="space-y-3">
                  {rows.map((row) => (
                    <div className="flex items-center justify-between text-xs gap-3" key={row.query_id}>
                      <span className="w-16 font-mono text-slate-500 truncate">Q{row.query_id}</span>
                      <div className="flex-1 bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-indigo-600 h-full rounded-full transition-all"
                          style={{ width: `${Math.min(100, Math.max(10, row.citations_count * 20))}%` }}
                        />
                      </div>
                      <strong className="w-24 text-right text-slate-700 font-mono">{row.citations_count} citations</strong>
                    </div>
                  ))}
                </div>
              </div>

              {/* Data Table */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100 text-xs text-left">
                    <thead>
                      <tr className="text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                        <th className="py-2.5 pr-4">Query</th>
                        <th className="py-2.5 px-4 text-center">Time</th>
                        <th className="py-2.5 px-4 text-center">Citations</th>
                        <th className="py-2.5 px-4 text-center">Evidence</th>
                        <th className="py-2.5 px-4 text-center">Warnings</th>
                        <th className="py-2.5 pl-4 text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-650">
                      {rows.map((row) => (
                        <tr key={row.query_id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="py-3 pr-4 font-medium text-slate-800">{row.query_text}</td>
                          <td className="py-3 px-4 text-center font-mono">{row.time_to_useful_answer_ms} ms</td>
                          <td className="py-3 px-4 text-center">{row.citations_count} citations</td>
                          <td className="py-3 px-4 text-center">{row.evidence_count} items</td>
                          <td className="py-3 px-4 text-center">{row.warnings_count}</td>
                          <td className="py-3 pl-4 text-right font-mono font-bold text-indigo-600">{row.evidence_usefulness_score ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Right Sidebar: Runs list */}
        <aside className="w-80 border-l border-slate-200 bg-white flex flex-col shrink-0 p-5 overflow-hidden">
          <h2 className="font-semibold text-slate-800 text-xs uppercase tracking-wider mb-4 border-b border-slate-150 pb-2">
            Past result runs
          </h2>
          <div className="flex-1 overflow-y-auto space-y-2.5">
            {runs.length === 0 ? (
              <p className="text-xs text-slate-400 italic text-center py-12">No result runs saved.</p>
            ) : (
              runs.map((run) => (
                <button
                  type="button"
                  key={run.run_id}
                  className={`w-full text-left p-3 rounded-lg border text-xs flex flex-col gap-1 transition-all cursor-pointer ${
                    selectedRun?.run_id === run.run_id
                      ? "border-indigo-500 bg-indigo-50/50 text-indigo-950 font-medium shadow-sm"
                      : "border-slate-200 hover:bg-slate-50 text-slate-600"
                  }`}
                  onClick={() => setSelectedRun(run)}
                >
                  <strong className="font-mono block truncate">{run.run_id}</strong>
                  <span className="text-[10px] text-slate-400">{run.repo} • {run.target_branch}</span>
                </button>
              ))
            )}
          </div>
        </aside>

      </div>

      {/* Footer */}
      <footer className="h-10 bg-white border-t border-slate-200 px-6 shrink-0 flex items-center justify-between text-xs text-slate-400">
        <div>DevOnboard Architecture Indexer</div>
        <div className="flex items-center space-x-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>Sync engine ready</span>
        </div>
      </footer>
    </main>
  );
}
