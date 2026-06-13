"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Loader2, Play } from "lucide-react";

type MetricRow = {
  query_id: number;
  query_text: string;
  mode: "devonboard" | "plain_agent";
  time_to_useful_answer_ms: number;
  citations_count: number;
  evidence_count: number;
  evidence_usefulness_score?: number | null;
  human_quality_score?: number | null;
};

type BenchmarkRun = {
  run_id: string;
  repo: string;
  target_branch: string;
  target_commit?: string | null;
  rows: MetricRow[];
  created_at: string;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function BenchmarkPage() {
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<BenchmarkRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const response = await fetch(`${backendUrl}/benchmark/results`);
      if (!response.ok) return;
      const payload = (await response.json()) as BenchmarkRun[];
      setRuns(payload);
      setSelectedRun((current) => current || payload[0] || null);
    } catch {
      setBanner("Benchmark API unavailable - start FastAPI before running comparisons.");
    }
  }

  async function runBenchmark() {
    setIsRunning(true);
    setBanner(null);
    try {
      const response = await fetch(`${backendUrl}/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo: "demo", target_branch: "dev" }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Benchmark failed.");
      await loadRuns();
    } catch (error) {
      setBanner(error instanceof Error ? error.message : "Benchmark failed.");
    } finally {
      setIsRunning(false);
    }
  }

  const rows = selectedRun?.rows || [];

  return (
    <main className="benchmark-shell" aria-label="Benchmark dashboard">
      <nav className="top-nav" aria-label="Benchmark status">
        <a href="/" className="back-link">
          <ArrowLeft size={16} aria-hidden="true" />
          Workspace
        </a>
        <div className="status-group">
          <span className="status-pill">DevOnboard vs plain-agent</span>
          <button type="button" className="status-action" onClick={runBenchmark} disabled={isRunning}>
            {isRunning ? <Loader2 size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
            Run Benchmark
          </button>
        </div>
      </nav>

      {banner ? <div className="banner">{banner}</div> : null}

      <section className="benchmark-layout">
        <section className="benchmark-main">
          <div className="benchmark-header">
            <BarChart3 size={20} aria-hidden="true" />
            <div>
              <h1>DevOnboard vs plain-agent</h1>
              <p>Compare cited graph retrieval against an uncited baseline across the fixed demo query set.</p>
            </div>
          </div>

          {rows.length === 0 ? (
            <div className="empty-benchmark">
              <p>Run a benchmark to compare DevOnboard with a plain-agent answer.</p>
              <button type="button" onClick={runBenchmark}>Run Benchmark</button>
            </div>
          ) : (
            <>
              <div className="chart-strip" aria-label="Citation count chart">
                {rows
                  .filter((row) => row.mode === "devonboard")
                  .map((row) => (
                    <div className="chart-row" key={row.query_id}>
                      <span>Q{row.query_id}</span>
                      <div>
                        <i style={{ width: `${Math.max(8, row.citations_count * 24)}px` }} />
                      </div>
                      <strong>{row.citations_count} citations</strong>
                    </div>
                  ))}
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Query</th>
                      <th>Mode</th>
                      <th>Time</th>
                      <th>Citations</th>
                      <th>Evidence</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={`${row.query_id}-${row.mode}`}>
                        <td>{row.query_text}</td>
                        <td>{row.mode}</td>
                        <td>{row.time_to_useful_answer_ms} ms</td>
                        <td>{row.citations_count} citations</td>
                        <td>{row.evidence_count} items</td>
                        <td>{row.evidence_usefulness_score || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        <aside className="benchmark-runs">
          <h2>Past runs</h2>
          {runs.length === 0 ? (
            <p className="empty-copy">No benchmark runs saved.</p>
          ) : (
            runs.map((run) => (
              <button
                type="button"
                key={run.run_id}
                className={selectedRun?.run_id === run.run_id ? "run-row active" : "run-row"}
                onClick={() => setSelectedRun(run)}
              >
                <strong>{run.run_id}</strong>
                <span>{run.repo} · {run.target_branch}</span>
              </button>
            ))
          )}
        </aside>
      </section>
    </main>
  );
}
