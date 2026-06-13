"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Boxes,
  FileCode2,
  GitBranch,
  History,
  Loader2,
  PackageOpen,
  Play,
  Search,
  Send,
  Sparkles,
} from "lucide-react";

type Evidence = {
  node_id: string;
  type: string;
  label: string;
  summary: string;
  url?: string | null;
  score?: number | null;
};

type GraphNode = {
  id: string;
  type: string;
  name: string;
  summary: string;
  tags: string[];
  filePath?: string;
};

type KnowledgeGraph = {
  repo: { name: string; branch: string; commit?: string | null };
  nodes: GraphNode[];
};

type Turn = {
  query: string;
  answer: string;
  route: string;
  citations: Evidence[];
  structural: Evidence[];
  historical: Evidence[];
  warnings: string[];
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const targetRepoPath = process.env.NEXT_PUBLIC_TARGET_REPO_PATH || "./target_repo";

const demoQueries = [
  "How does the agent pipeline execute a tool call?",
  "Why was progressive memory loading chosen?",
  "Is it safe to refactor ProviderAdapter?",
  "What should I inspect before reviewing changes touching ProviderAdapter?",
  "Create a cited context pack for an agent modifying the provider subsystem.",
];

export default function Home() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [historyEvidence, setHistoryEvidence] = useState<{
    evidence: Evidence[];
    claims: Evidence[];
    risks: Evidence[];
    warnings: string[];
  }>({ evidence: [], claims: [], risks: [], warnings: [] });
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("auto");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [scanStatus, setScanStatus] = useState("idle");
  const [ingestStatus, setIngestStatus] = useState("idle");
  const [isAsking, setIsAsking] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [packMarkdown, setPackMarkdown] = useState<string | null>(null);

  const graphNodes = useMemo(
    () => (graph?.nodes || []).filter((node) => ["file", "function", "module", "class"].includes(node.type)),
    [graph],
  );

  useEffect(() => {
    loadGraph();
  }, []);

  async function loadGraph() {
    try {
      const health = await fetch(`${backendUrl}/health`);
      if (!health.ok) return;
      const healthPayload = await health.json();
      if (!healthPayload.graph_exists) return;
      const response = await fetch(`${backendUrl}/graph`);
      if (!response.ok) return;
      const payload = (await response.json()) as KnowledgeGraph;
      setGraph(payload);
      setSelectedNode((current) => current || payload.nodes[0] || null);
    } catch {
      setBanner("Backend unavailable — start FastAPI to load the graph.");
    }
  }

  async function runScan() {
    setScanStatus("scanning");
    setBanner(null);
    const response = await fetch(`${backendUrl}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_path: targetRepoPath, branch: "dev", exclude_patterns: [] }),
    });
    const payload = await response.json();
    setScanStatus(String(payload.status || "done"));
    if (!response.ok) setBanner(payload.detail || "Scan failed.");
    await loadGraph();
  }

  async function ingestHistory() {
    setIngestStatus("ingesting");
    setBanner(null);
    const response = await fetch(`${backendUrl}/ingest/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_commits: 500 }),
    });
    const payload = await response.json();
    setIngestStatus(String(payload.status || "done"));
    if (!response.ok) setBanner(payload.detail || "History ingest failed.");
    await loadGraph();
  }

  async function selectNode(node: GraphNode) {
    setSelectedNode(node);
    setPackMarkdown(null);
    try {
      const response = await fetch(`${backendUrl}/graph/node/${encodeURIComponent(node.id)}/history`);
      if (!response.ok) return;
      setHistoryEvidence(await response.json());
    } catch {
      setHistoryEvidence({
        evidence: [],
        claims: [],
        risks: [],
        warnings: ["History unavailable — backend request failed."],
      });
    }
  }

  async function ask(event?: FormEvent, forcedQuery?: string) {
    event?.preventDefault();
    const activeQuery = forcedQuery || query.trim();
    if (!activeQuery) return;
    setIsAsking(true);
    setQuery("");
    setBanner(null);
    try {
      const response = await fetch(`${backendUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: activeQuery,
          mode,
          node_ids: selectedNode ? [selectedNode.id] : [],
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Query failed.");
      setTurns((current) => [...current, { query: activeQuery, ...payload }]);
    } catch (error) {
      setBanner(error instanceof Error ? error.message : "Query failed.");
    } finally {
      setIsAsking(false);
    }
  }

  async function generatePack() {
    const response = await fetch(`${backendUrl}/evidence-packs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        purpose: "pr_review",
        node_ids: selectedNode ? [selectedNode.id] : [],
        changed_files: selectedNode?.filePath ? [selectedNode.filePath] : [],
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setBanner(payload.detail || "Evidence pack generation failed.");
      return;
    }
    setPackMarkdown(payload.markdown);
  }

  return (
    <main className="app-shell" aria-label="DevOnboard workspace">
      <nav className="top-nav" aria-label="Workspace status">
        <div className="repo-chip">
          <GitBranch size={16} aria-hidden="true" />
          <span>{graph?.repo.name || "target_repo"}</span>
          <code>{graph?.repo.branch || "dev"}</code>
        </div>
        <div className="status-group">
          <button type="button" className="status-action" onClick={runScan}>
            {scanStatus === "scanning" ? <Loader2 size={14} /> : <Play size={14} />}
            Run Scan
          </button>
          <button type="button" className="status-action" onClick={ingestHistory}>
            {ingestStatus === "ingesting" ? <Loader2 size={14} /> : <History size={14} />}
            Ingest History
          </button>
          <a href="/benchmark">Benchmark</a>
        </div>
      </nav>

      {banner ? <div className="banner">{banner}</div> : null}

      <section className="workspace-grid">
        <aside className="left-panel" aria-label="Graph and file navigation">
          <div className="panel-header">
            <span>Files / Graph</span>
            <Search size={14} aria-hidden="true" />
          </div>
          <div className="node-list">
            {graphNodes.length === 0 ? (
              <p className="empty-copy">No graph found. Click Run Scan to get started.</p>
            ) : (
              graphNodes.slice(0, 80).map((node) => (
                <button
                  key={node.id}
                  type="button"
                  className={selectedNode?.id === node.id ? "node-row active" : "node-row"}
                  onClick={() => selectNode(node)}
                >
                  {node.type === "module" ? <Boxes size={14} /> : <FileCode2 size={14} />}
                  <span>{node.filePath || node.name}</span>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="chat-panel" aria-label="Cited question and answer thread">
          <div className="thread">
            {turns.length === 0 ? (
              <div className="assistant-intro">
                <Sparkles size={18} aria-hidden="true" />
                <div>
                  <h1>Ask about code history with citations.</h1>
                  <p>
                    DevOnboard keeps the Claude-like chat flow centered, while graph nodes,
                    evidence, and History/Why stay visible for verification.
                  </p>
                </div>
              </div>
            ) : (
              turns.map((turn, index) => <AnswerTurn key={`${turn.query}-${index}`} turn={turn} />)
            )}

            <div className="suggestions" aria-label="Suggested demo queries">
              {demoQueries.map((item) => (
                <button key={item} type="button" onClick={() => ask(undefined, item)}>
                  {item}
                </button>
              ))}
            </div>
          </div>

          <form className="composer" aria-label="Ask DevOnboard" onSubmit={(event) => ask(event)}>
            <label htmlFor="query">Query</label>
            <select value={mode} onChange={(event) => setMode(event.target.value)} aria-label="Query mode">
              <option value="auto">Auto</option>
              <option value="structural">Structural</option>
              <option value="historical">Historical</option>
              <option value="hybrid">Hybrid</option>
            </select>
            <textarea
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask a cited question about this repo..."
              rows={2}
            />
            <button type="submit" disabled={isAsking}>
              {isAsking ? <Loader2 size={16} aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
              Ask
            </button>
          </form>
        </section>

        <aside className="right-panel" aria-label="History and why inspector">
          <div className="panel-header">
            <span>History / Why</span>
            <PackageOpen size={14} aria-hidden="true" />
          </div>
          <div className="selected-node">
            <strong>{selectedNode?.name || "No node selected"}</strong>
            <span>{selectedNode?.id || "Select a file, function, or module to see context."}</span>
          </div>
          <EvidenceSection title="Linked Commits/PRs" items={historyEvidence.evidence} empty="No linked commits found." />
          <EvidenceSection title="Claims" items={historyEvidence.claims} empty="No claims found." />
          <EvidenceSection title="Risks" items={historyEvidence.risks} empty="No risks found." />
          {historyEvidence.warnings.map((warning) => (
            <div className="warning" key={warning}>{warning}</div>
          ))}
          <button type="button" className="pack-button" onClick={generatePack}>
            Generate Evidence Pack
          </button>
          {packMarkdown ? <pre className="pack-preview">{packMarkdown}</pre> : null}
        </aside>
      </section>
    </main>
  );
}

function AnswerTurn({ turn }: { turn: Turn }) {
  return (
    <article className="turn">
      <p className="user-query">{turn.query}</p>
      <div className="route-badge">{turn.route}</div>
      <div className="answer-body">{turn.answer}</div>
      <div className="citation-row">
        {turn.citations.map((citation, index) => (
          <button type="button" key={citation.node_id} className="citation-chip">
            [{index + 1}] {citation.label}
          </button>
        ))}
      </div>
      {turn.warnings.map((warning) => (
        <div className="warning" key={warning}>{warning}</div>
      ))}
    </article>
  );
}

function EvidenceSection({ title, items, empty }: { title: string; items: Evidence[]; empty: string }) {
  return (
    <section className="evidence-section">
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="empty-copy">{empty}</p>
      ) : (
        items.map((item) => (
          <button type="button" className="citation-card" key={item.node_id}>
            <span className={`evidence-badge ${item.type}`}>{item.type}</span>
            <strong>{item.label}</strong>
            <span>{item.summary}</span>
          </button>
        ))
      )}
    </section>
  );
}
