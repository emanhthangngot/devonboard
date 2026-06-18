"use client";

import React, { useState, useEffect, useRef, useMemo, FormEvent } from "react";
import {
  Play,
  RefreshCw,
  Search,
  FileCode,
  Folder,
  BookOpen,
  Terminal,
  History,
  User,
  Cpu,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  MessageSquare,
  Zap,
  Award,
  ArrowRight,
  Download,
  GitBranch,
  Activity,
  FileText,
  HelpCircle,
  Clock,
  XCircle,
  Boxes,
  Loader2,
  ClipboardCopy,
  ArrowLeft,
  BarChart3
} from "lucide-react";
import { NodeType, EdgeType, KnowledgeGraph, GraphNode, GraphEdge, ChatMessage, BenchmarkResult } from "./types";
import { ArchitectureGraph } from "./components/ArchitectureGraph";

type Evidence = {
  node_id: string;
  type: string;
  label: string;
  summary: string;
  url?: string | null;
  score?: number | null;
};

type HealthStatus = {
  status: string;
  graph_exists?: boolean;
  target_repo?: { path: string; branch: string; commit?: string | null };
  graph_repo?: { name: string; path?: string; branch: string; commit?: string | null } | null;
};

type GraphSummary = {
  version: string;
  generated_at: string;
  repo: KnowledgeGraph["repo"];
  total_nodes: number;
  total_edges: number;
};

type GraphNodesResponse = {
  nodes: GraphNode[];
  next_cursor: number | null;
  total: number;
};

type JobStatus = {
  status: string;
  progress?: number;
  message?: string | null;
  warnings?: string[];
  error?: string | null;
};

const jobPollIntervalMs = process.env.NODE_ENV === "test" ? 0 : 1000;
const jobPollTimeoutMs = 120_000;

type NodeHistory = {
  evidence: Evidence[];
  claims: Evidence[];
  risks: Evidence[];
  warnings: string[];
};

type QueryTurn = {
  id: string;
  query: string;
  answer: string;
  route: string;
  citations: Evidence[];
  structural: Evidence[];
  historical: Evidence[];
  warnings: string[];
  retrieval_ms?: number;
  synthesis_ms?: number;
  evidence_only?: boolean;
  status: "running" | "done" | "error";
};

type EvidencePack = {
  purpose: "pr_review" | "ai_agent_context";
  markdown: string;
  citations: Evidence[];
  warnings: string[];
  excluded_sources: string[];
  evidence_only?: boolean;
};

type ResultRun = {
  run_id: string;
  repo: string;
  target_branch: string;
  target_commit?: string | null;
  rows: {
    query_id: number;
    query_text: string;
    time_to_useful_answer_ms: number;
    citations_count: number;
    evidence_count: number;
    warnings_count: number;
    evidence_usefulness_score?: number | null;
    human_quality_score?: number | null;
  }[];
  created_at: string;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const defaultRepoPath = process.env.NEXT_PUBLIC_TARGET_REPO_PATH || "./target_repo";
const storageKey = "devonboard.repoPath";

const emptyHistory: NodeHistory = { evidence: [], claims: [], risks: [], warnings: [] };

export default function Home() {
  // Navigation Mode: "workspace" | "graph" | "benchmark"
  const [viewMode, setViewMode] = useState<"workspace" | "graph" | "benchmark">("workspace");

  // Repository configuration
  const [repoPath, setRepoPath] = useState(defaultRepoPath);
  const [branch, setBranch] = useState("dev");
  const [commit, setCommit] = useState<string | null>(null);

  // Core Data
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [historyEvidence, setHistoryEvidence] = useState<NodeHistory>(emptyHistory);

  // Status & Progress Pipelines
  const [scanStatus, setScanStatus] = useState<JobStatus>({ status: "idle", progress: 0 });
  const [ingestStatus, setIngestStatus] = useState<JobStatus>({ status: "idle", progress: 0 });
  const [banner, setBanner] = useState<{ tone: "error" | "warning" | "info"; message: string } | null>(null);

  // Search & Filter
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("auto"); // query mode: "auto", "structural", etc.

  // Chat / Q&A turns
  const [turns, setTurns] = useState<QueryTurn[]>([]);
  const [isAsking, setIsAsking] = useState(false);

  // Evidence Pack Modal State
  const [packPurpose, setPackPurpose] = useState<"pr_review" | "ai_agent_context">("pr_review");
  const [pack, setPack] = useState<EvidencePack | null>(null);
  const [isPackOpen, setIsPackOpen] = useState(false);
  const [isGeneratingPack, setIsGeneratingPack] = useState(false);
  const [copyState, setCopyState] = useState("");

  // Benchmark Results View
  const [benchmarkRuns, setBenchmarkRuns] = useState<ResultRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<ResultRun | null>(null);
  const [benchmarkLoading, setBenchmarkLoading] = useState(false);

  // Refs for scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isMounted = useRef(true);

  // Load initial settings and graph
  useEffect(() => {
    isMounted.current = true;
    const storedPath = safeStorageGet(storageKey);
    if (storedPath) setRepoPath(storedPath);
    loadInitialContext(storedPath || defaultRepoPath);
    loadBenchmarkRuns();
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [turns]);

  const graphMissing = !graph || !graph.nodes || graph.nodes.length === 0;

  async function loadInitialContext(fallbackPath: string) {
    try {
      const health = await requestJson<HealthStatus>("/health");
      if (!isMounted.current) return;
      const activeRepo = health.graph_repo || health.target_repo;
      if (activeRepo?.path && !safeStorageGet(storageKey)) setRepoPath(activeRepo.path);
      if (activeRepo?.branch) setBranch(activeRepo.branch);
      if (activeRepo?.commit) setCommit(activeRepo.commit);
      if (health.graph_exists) await loadGraph();
    } catch {
      if (isMounted.current) {
        setBanner({ tone: "error", message: "Backend unavailable. Start FastAPI before scanning or querying." });
        setRepoPath(fallbackPath);
      }
    }
  }

  async function loadGraph() {
    try {
      const payload = await loadNavigationGraph();
      if (!isMounted.current) return;
      setGraph(payload);
      setRepoPath((current) => current || payload.repo?.path || defaultRepoPath);
      setBranch(payload.repo?.branch || "dev");
      setCommit(payload.repo?.commit || null);
      
      const initialNode = selectedNode ? payload.nodes.find((node) => node.id === selectedNode.id) : payload.nodes[0];
      setSelectedNode(initialNode || null);
      if (initialNode) await selectNode(initialNode);
    } catch (error) {
      if (isMounted.current) {
        setGraph(null);
        setSelectedNode(null);
        setHistoryEvidence(emptyHistory);
        setBanner({ tone: "warning", message: errorMessage(error, "No graph found. Run Scan to get started.") });
      }
    }
  }

  async function runScan() {
    const activePath = repoPath.trim();
    if (!activePath) {
      setBanner({ tone: "error", message: "Enter a local repository path or GitHub URL before scanning." });
      return;
    }
    safeStorageSet(storageKey, activePath);
    setScanStatus({ status: "running", progress: 10, message: "Scanning repository." });
    setBanner(null);
    try {
      const payload = await requestJson<JobStatus>("/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: activePath, branch, commit, exclude_patterns: [] }),
      });
      setScanStatus(payload);
      const finalStatus = await pollJobStatus("/scan/status", setScanStatus);
      if (finalStatus.status === "error") {
        throw new Error(finalStatus.error || "Scan failed.");
      }
      await loadGraph();
    } catch (error) {
      const message = errorMessage(error, "Scan failed.");
      setScanStatus({ status: "error", progress: 0, error: message });
      setBanner({ tone: "error", message });
    }
  }

  async function ingestHistory() {
    const activePath = repoPath.trim();
    if (!activePath) {
      setBanner({ tone: "error", message: "Enter a local repository path or GitHub URL before ingesting history." });
      return;
    }
    safeStorageSet(storageKey, activePath);
    setIngestStatus({ status: "running", progress: 10, message: "Ingesting history." });
    setBanner(null);
    try {
      const payload = await requestJson<JobStatus>("/ingest/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: activePath, branch, commit, max_commits: 500 }),
      });
      setIngestStatus(payload);
      const finalStatus = await pollJobStatus("/ingest/history/status", setIngestStatus);
      if (finalStatus.status === "error") {
        throw new Error(finalStatus.error || "History ingest failed.");
      }
      await loadGraph();
    } catch (error) {
      const message = errorMessage(error, "History ingest failed.");
      setIngestStatus({ status: "error", progress: 0, error: message });
      setBanner({ tone: "error", message });
    }
  }

  async function loadNavigationGraph(): Promise<KnowledgeGraph> {
    try {
      const summary = await requestJson<GraphSummary>("/graph/summary");
      if (!summary?.repo || typeof summary.version !== "string") {
        throw new Error("Graph summary unavailable.");
      }
      const [claims, files, members] = await Promise.all([
        requestJson<GraphNodesResponse>("/graph/nodes?type=claim,topic&limit=500"),
        requestJson<GraphNodesResponse>("/graph/nodes?type=file,module,config&limit=1000"),
        requestJson<GraphNodesResponse>("/graph/nodes?type=function,class,service,endpoint,domain,flow,step&limit=50"),
      ]);
      const nodesById = new Map<string, GraphNode>();
      for (const node of [...(claims.nodes || []), ...(files.nodes || []), ...(members.nodes || [])]) {
        nodesById.set(node.id, node);
      }
      return {
        version: summary.version,
        generated_at: summary.generated_at,
        repo: summary.repo,
        nodes: [...nodesById.values()],
        edges: [],
      };
    } catch {
      return requestJson<KnowledgeGraph>("/graph");
    }
  }

  async function selectNode(node: GraphNode) {
    setSelectedNode(node);
    setPack(null);
    try {
      const payload = await requestJson<NodeHistory>(`/graph/node/${encodeURIComponent(node.id)}/history`);
      setHistoryEvidence(payload);
    } catch {
      setHistoryEvidence({
        evidence: [],
        claims: [],
        risks: [],
        warnings: ["History unavailable. Backend could not load node evidence."],
      });
    }
  }

  async function ask(event?: FormEvent, forcedQuery?: string) {
    event?.preventDefault();
    const activeQuery = (forcedQuery || query).trim();
    if (!activeQuery || isAsking) return;
    const id = `${Date.now()}-${activeQuery}`;
    setQuery("");
    setIsAsking(true);
    setBanner(null);
    setTurns((current) => [
      ...current,
      {
        id,
        query: activeQuery,
        answer: "",
        route: mode,
        citations: [],
        structural: [],
        historical: [],
        warnings: [],
        status: "running",
      },
    ]);
    try {
      const response = await fetch(`${backendUrl}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: activeQuery,
          mode,
          node_ids: [],
          allow_external_llm_for_private_repo: true,
        }),
      });

      if (!response.ok) {
        let errMsg = `Server returned status ${response.status}`;
        try {
          const payload = await response.json();
          errMsg = payload?.error?.message || payload?.detail || errMsg;
        } catch {}
        throw new Error(errMsg);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Readable stream not supported");
      }

      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = "";
          let dataStr = "";

          const lines = part.split("\n");
          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.substring(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr = line.substring(5).trim();
            }
          }

          if (!eventType || !dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            if (eventType === "route") {
              setTurns((current) => current.map((t) => (t.id === id ? { ...t, route: data.route } : t)));
            } else if (eventType === "citations") {
              setTurns((current) => current.map((t) => (t.id === id ? { ...t, citations: data.citations } : t)));
            } else if (eventType === "warnings") {
              setTurns((current) => current.map((t) => (t.id === id ? { ...t, warnings: data.warnings } : t)));
            } else if (eventType === "token") {
              setTurns((current) =>
                current.map((t) => {
                  if (t.id === id) {
                    return { ...t, answer: t.answer + data.token };
                  }
                  return t;
                })
              );
            }
          } catch (e) {
            console.error("Failed to parse SSE data:", e);
          }
        }
      }

      setTurns((current) => current.map((t) => (t.id === id ? { ...t, status: "done" } : t)));
    } catch (error) {
      const message = errorMessage(error, "Query failed.");
      setTurns((current) => current.map((t) => (t.id === id ? { ...t, answer: message, status: "error", warnings: [message] } : t)));
      setBanner({ tone: "error", message });
    } finally {
      setIsAsking(false);
    }
  }

  async function jumpToCitation(citation: Evidence) {
    const target = graph?.nodes.find((node) => node.id === citation.node_id);
    if (target) await selectNode(target);
    else setBanner({ tone: "info", message: "Citation source is evidence-only and has no selectable graph node." });
  }

  async function generatePack(purpose = packPurpose) {
    setIsPackOpen(true);
    setIsGeneratingPack(true);
    setPack(null);
    setBanner(null);
    try {
      const payload = await requestJson<EvidencePack>("/evidence-packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          purpose,
          node_ids: selectedNode ? [selectedNode.id] : [],
          changed_files: selectedNode?.metadata?.path ? [selectedNode.metadata.path] : [],
        }),
      });
      setPack(payload);
    } catch (error) {
      setBanner({ tone: "error", message: errorMessage(error, "Evidence pack generation failed.") });
    } finally {
      setIsGeneratingPack(false);
    }
  }

  async function copyPack() {
    if (!pack?.markdown || !navigator.clipboard) return;
    await navigator.clipboard.writeText(pack.markdown);
    setCopyState("Copied to clipboard");
    window.setTimeout(() => setCopyState(""), 1400);
  }

  function exportPack() {
    if (!pack?.markdown) return;
    const blob = new Blob([pack.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `evidence-pack-${packPurpose}-${selectedNode?.id || "repo"}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  // Benchmark / Results Logic
  async function loadBenchmarkRuns() {
    try {
      const response = await fetch(`${backendUrl}/results/runs`);
      if (!response.ok) {
        setBenchmarkRuns([]);
        return;
      }
      const payload = (await response.json()) as ResultRun[];
      if (Array.isArray(payload)) {
        setBenchmarkRuns(payload);
        setSelectedRun((current) => current || payload[0] || null);
      } else {
        setBenchmarkRuns([]);
      }
    } catch {
      setBenchmarkRuns([]);
    }
  }

  async function runResults() {
    setBenchmarkLoading(true);
    setBanner(null);
    try {
      const response = await fetch(`${backendUrl}/results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo: "demo", target_branch: "dev" }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Result run failed.");
      await loadBenchmarkRuns();
    } catch (error) {
      setBanner({ tone: "error", message: error instanceof Error ? error.message : "Result run failed." });
    } finally {
      setBenchmarkLoading(false);
    }
  }

  // Filter lists in left sidebar
  const filteredClaims = useMemo(() => {
    const term = filter.trim().toLowerCase();
    return (graph?.nodes || [])
      .filter((n) => n.type === "claim" || n.type === "topic")
      .filter((n) => !term || [n.name, n.id, n.metadata?.description || ""].join(" ").toLowerCase().includes(term));
  }, [graph, filter]);

  const filteredFiles = useMemo(() => {
    const term = filter.trim().toLowerCase();
    return (graph?.nodes || [])
      .filter((n) => n.type === "file" || n.type === "module" || n.type === "config")
      .filter((n) => !term || [n.name, n.id, n.metadata?.path || "", n.metadata?.description || ""].join(" ").toLowerCase().includes(term));
  }, [graph, filter]);

  const filteredMembers = useMemo(() => {
    const term = filter.trim().toLowerCase();
    const allowed = ["function", "class", "service", "endpoint", "domain", "flow", "step"];
    return (graph?.nodes || [])
      .filter((n) => allowed.includes(n.type))
      .filter((n) => !term || [n.name, n.id, n.metadata?.description || ""].join(" ").toLowerCase().includes(term))
      .slice(0, 50);
  }, [graph, filter]);

  // Format code references inside answers dynamically
  const renderFormattedMarkdown = (text: string) => {
    if (!text) return null;
    const parts = text.split(/(\[source:commit:\w+\]|\[node:file:[\w./-]+\]|\[node:claim:\w+\])/g);

    return parts.map((part, index) => {
      const sourceMatch = part.match(/\[source:commit:(\w+)\]/);
      const fileMatch = part.match(/\[node:file:([\w./-]+)\]/);
      const claimMatch = part.match(/\[node:claim:(\w+)\]/);

      if (sourceMatch) {
        const hash = sourceMatch[1];
        return (
          <button
            key={index}
            onClick={() => {
              const nd = graph?.nodes.find(n => n.id.includes(hash) || (n.metadata?.hash && n.metadata.hash.includes(hash)));
              if (nd) selectNode(nd);
            }}
            className="px-1.5 py-0.5 rounded text-xs font-mono bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition-colors inline-block align-middle my-0.5"
          >
            📋 Commit: {hash}
          </button>
        );
      } else if (fileMatch) {
        const pathStr = fileMatch[1];
        return (
          <button
            key={index}
            onClick={() => {
              const nd = graph?.nodes.find(n => n.type === "file" && (n.metadata?.path === pathStr || n.name === pathStr));
              if (nd) selectNode(nd);
            }}
            className="px-1.5 py-0.5 rounded text-xs font-mono bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 transition-colors inline-block align-middle my-0.5"
          >
            📁 {pathStr}
          </button>
        );
      } else if (claimMatch) {
        const claimId = claimMatch[1];
        return (
          <button
            key={index}
            onClick={() => {
              const nd = graph?.nodes.find(n => n.type === "claim" && (n.id.includes(claimId) || n.name.toLowerCase().includes(claimId.toLowerCase())));
              if (nd) selectNode(nd);
            }}
            className="px-1.5 py-0.5 rounded text-xs font-medium bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 transition-colors inline-block align-middle my-0.5"
          >
            💡 Decision: {claimId}
          </button>
        );
      }

      const boldParts = part.split(/(\*\*.*?\*\*)/g);
      return boldParts.map((bp, bIndex) => {
        if (bp.startsWith("**") && bp.endsWith("**")) {
          return <strong key={bIndex} className="font-semibold text-gray-900">{bp.slice(2, -2)}</strong>;
        }
        return bp;
      });
    });
  };

  // Helper badge class style
  const badgeClass = (type: string) => {
    if (["file", "function", "class", "module", "service", "endpoint", "config", "domain", "flow", "step"].includes(type)) return "bg-blue-50 text-blue-700 border-blue-200";
    if (["claim", "topic"].includes(type)) return "bg-amber-50 text-amber-700 border-amber-200";
    if (type.includes("risk") || type.includes("contradiction")) return "bg-rose-50 text-rose-700 border-rose-200 animate-pulse";
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden selection:bg-indigo-100 selection:text-indigo-900">
      
      {/* 1. Header Navigation Bar */}
      <nav id="top-nav" className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0 relative z-30">
        <div className="flex items-center space-x-4">
          <div className="w-8 h-8 bg-indigo-600 rounded flex items-center justify-center text-white font-bold">D</div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">DevOnboard</h1>
          <div className="flex items-center px-2 py-0.5 bg-slate-100 rounded border border-slate-200 text-xs font-mono text-slate-600">
            <GitBranch className="w-3 h-3 mr-1.5" />
            <span>{branch || "dev"}</span>
          </div>
        </div>

        {/* Dynamic Scan Pipelines and Tab Navigator */}
        <div className="flex items-center space-x-3">
          
          <button
            id="btn-run-scan"
            onClick={runScan}
            disabled={scanStatus.status === "running"}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-350 disabled:cursor-not-allowed rounded-md text-xs font-medium shadow-sm transition-colors cursor-pointer flex items-center gap-1.5"
          >
            {scanStatus.status === "running" ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <Play className="w-3 h-3" />
            )}
            <span>Run Scan</span>
          </button>

          <button
            id="btn-ingest-history"
            onClick={ingestHistory}
            disabled={ingestStatus.status === "running"}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1.5"
          >
            {ingestStatus.status === "running" ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
            )}
            <span>Ingest History</span>
          </button>

          {/* Export Pack */}
          <button
            id="btn-export-pack"
            onClick={() => generatePack()}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer flex items-center gap-1"
          >
            <Download className="w-3 h-3 text-slate-400" />
            <span>Generate Evidence Pack</span>
          </button>

          {/* Tab Selection */}
          <div className="bg-slate-100 p-1 rounded-md border border-slate-200 flex items-center gap-0.5">
            <button
              id="tab-view-workspace"
              onClick={() => setViewMode("workspace")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                viewMode === "workspace"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Workspace
            </button>
            <button
              id="tab-view-graph"
              onClick={() => setViewMode("graph")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                viewMode === "graph"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Architecture Map
            </button>
            <button
              id="tab-view-benchmark"
              onClick={() => setViewMode("benchmark")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                viewMode === "benchmark"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Benchmark
            </button>
          </div>

        </div>
      </nav>

      {/* Banner message alert */}
      {banner && (
        <div className={`px-6 py-2 text-xs border-b flex items-center justify-between shrink-0 ${
          banner.tone === "error" ? "bg-rose-50 border-rose-100 text-rose-950" : 
          banner.tone === "warning" ? "bg-amber-50 border-amber-100 text-amber-950" : 
          "bg-blue-50 border-blue-100 text-blue-950"
        }`}>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{banner.message}</span>
          </div>
          <button onClick={() => setBanner(null)} className="font-semibold cursor-pointer">×</button>
        </div>
      )}

      {/* Pipeline Status Progress Display */}
      {(scanStatus.status === "running" || ingestStatus.status === "running") && (
        <div id="pipeline-status-banner" className="bg-indigo-50 border-b border-indigo-100 px-6 py-2 flex items-center justify-between gap-3 text-xs text-indigo-900 shrink-0">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-indigo-600 animate-pulse" />
            <span>
              {scanStatus.status === "running"
                ? `[Scan] File Scanner: scanning target repo...`
                : `[Ingest] Extraction: ingesting repository git logs...`}
            </span>
          </div>
          <div className="w-48 bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-300"
              style={{
                width: `${scanStatus.status === "running" ? (scanStatus.progress || 50) : (ingestStatus.progress || 50)}%`
              }}
            />
          </div>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 flex overflow-hidden" aria-label="DevOnboard workspace">
        
        {/* A. LEFT COLUMN: Directory Tree & Graph node browser */}
        <aside id="left-column" className={`w-64 border-r border-slate-200 bg-white flex flex-col shrink-0 overflow-hidden ${viewMode === "benchmark" ? "hidden" : ""}`} aria-label="Graph and file navigation">
          
          {/* Target Repo Config Panel */}
          <section className="p-4 border-b border-slate-100 bg-slate-50 space-y-3" aria-label="Repository context">
            <label className="block text-xs font-semibold text-slate-500">
              Repository path or GitHub URL
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                placeholder="./target_repo or https://github.com/owner/repo"
                className="w-full mt-1 px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-500">
              Branch
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="dev"
                className="w-full mt-1 px-2.5 py-1.5 bg-white border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </label>
            {graphMissing && (
              <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded p-2 flex items-start gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>No graph found. Run Scan to get started.</span>
              </div>
            )}
          </section>

          {/* Search/Filter box */}
          <div className="p-3 border-b border-slate-100">
            <div className="relative flex items-center bg-slate-50 border border-slate-200 rounded px-2.5 py-1 focus-within:ring-1 focus-within:ring-indigo-500 focus-within:bg-white transition-all">
              <Search className="w-3.5 h-3.5 text-slate-400 mr-2" />
              <input
                type="text"
                placeholder="Filter files & claims..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-transparent text-xs outline-none w-full"
              />
            </div>
          </div>

          {/* Scrollable Tree Navigation lists */}
          <div className="flex-1 p-2 space-y-4 overflow-y-auto">
            
            {/* Category 1: Design claims decisions */}
            <div>
              <span className="px-2 text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1.5">💡 Design Claims</span>
              <div className="space-y-0.5">
                {filteredClaims.map((node) => (
                  <button
                    key={node.id}
                    id={`node-claim-${node.id}`}
                    onClick={() => selectNode(node)}
                    className={`w-full text-left p-2 rounded text-xs flex items-start gap-2 transition-all cursor-pointer ${
                      selectedNode?.id === node.id
                        ? "bg-indigo-50 border-r-2 border-indigo-500 text-indigo-950 font-medium"
                        : "hover:bg-slate-50 text-slate-600"
                    }`}
                  >
                    <BookOpen className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${selectedNode?.id === node.id ? "text-indigo-600" : "text-slate-400"}`} />
                    <div className="min-w-0">
                      <div className="font-semibold truncate">{node.name}</div>
                      <div className="text-[10px] text-slate-400 truncate mt-0.5">{node.metadata?.tradeoffs?.substring(0, 48) || node.metadata?.description || "Source tradeoffs decision."}...</div>
                    </div>
                  </button>
                ))}
                {filteredClaims.length === 0 && (
                  <p className="text-[10px] text-slate-400 italic px-2">No matching design claims.</p>
                )}
              </div>
            </div>

            {/* Category 2: Scanned Files */}
            <div>
              <span className="px-2 text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1.5">📁 Scanned Files</span>
              <div className="space-y-0.5">
                {filteredFiles.map((node) => (
                  <button
                    key={node.id}
                    id={`node-file-${node.id}`}
                    onClick={() => selectNode(node)}
                    className={`w-full text-left p-2 rounded text-xs flex items-center justify-between gap-2.5 transition-all outline-none cursor-pointer ${
                      selectedNode?.id === node.id
                        ? "bg-indigo-50 border-r-2 border-indigo-500 text-indigo-950 font-medium"
                        : "hover:bg-slate-50 text-slate-500"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileCode className={`w-3.5 h-3.5 shrink-0 ${selectedNode?.id === node.id ? "text-indigo-500" : "text-slate-400"}`} />
                      <span className="truncate">{node.name}</span>
                    </div>
                    <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                  </button>
                ))}
                {filteredFiles.length === 0 && (
                  <p className="text-[10px] text-slate-400 italic px-2">No matching files.</p>
                )}
              </div>
            </div>

            {/* Category 3: Functions & Classes / Members */}
            <div>
              <span className="px-2 text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1.5">⚙️ Members</span>
              <div className="space-y-0.5">
                {filteredMembers.map((node) => (
                  <button
                    key={node.id}
                    id={`node-member-${node.id}`}
                    onClick={() => selectNode(node)}
                    className={`w-full text-left p-1.5 rounded text-[11px] flex items-center gap-2 transition-all cursor-pointer ${
                      selectedNode?.id === node.id
                        ? "bg-indigo-50 border-r-2 border-indigo-500 text-indigo-950 font-medium"
                        : "hover:bg-slate-50 text-slate-500"
                    }`}
                  >
                    <Terminal className="w-3 h-3 text-slate-400 shrink-0" />
                    <span className="truncate">{node.name} <span className="text-[9px] text-slate-400">({node.type})</span></span>
                  </button>
                ))}
                {filteredMembers.length === 0 && (
                  <p className="text-[10px] text-slate-400 italic px-2">No matching members.</p>
                )}
              </div>
            </div>

          </div>
        </aside>

        {/* B. MIDDLE COLUMN (Depends on Tab ViewMode) */}
        
        {/* View Mode: Workspace (RAG Chat View) */}
        <section id="middle-column-workspace" className={`flex-1 flex flex-col bg-slate-50 overflow-hidden h-full ${viewMode === "workspace" ? "" : "hidden"}`} aria-label="Cited question and answer thread">
          {/* Chat Messages Log */}
          <div className="flex-grow p-6 space-y-4 overflow-y-auto">
            {/* Initial Welcome message */}
            <div className="flex flex-col items-start">
              <div className="px-4 py-3 bg-white border border-slate-200 rounded-lg rounded-tl-none text-slate-900 text-sm space-y-2 p-4 shadow-sm max-w-[85%]">
                <p className="font-semibold text-slate-800">Hello! I am DevOnboard AI.</p>
                <p className="leading-relaxed text-slate-600">
                  I've indexed your codebase, linked commits metadata, and extracted core architectural design tradeoffs as a structured graph.
                </p>
                <p className="leading-relaxed text-slate-600">
                  Ask me anything about code flows, design constraints, file histories, or select files in the tree to analyze refactor risk indicators!
                </p>
              </div>
            </div>

            {/* Q&A Turns */}
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                {/* User Message */}
                <div className="flex flex-col items-end">
                  <div className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg rounded-tr-none shadow-sm max-w-[85%]">
                    {turn.query}
                  </div>
                </div>

                {/* Assistant Message */}
                <div className="flex flex-col items-start">
                  <div className="px-4 py-3 bg-white border border-slate-200 rounded-lg rounded-tl-none text-slate-900 text-sm space-y-3 p-4 shadow-sm max-w-[85%] w-full">
                    {turn.status === "running" ? (
                      <div className="flex items-center gap-2 text-slate-400">
                        <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                        <span>Searching graph memory and synthesizing answer...</span>
                      </div>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap leading-relaxed prose prose-sm max-w-none text-slate-700">
                          {renderFormattedMarkdown(turn.answer)}
                        </div>

                        {/* Citations Row */}
                        {turn.citations && turn.citations.length > 0 && (
                          <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap gap-1.5" aria-label="Answer citations">
                            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider block w-full mb-1">Citations:</span>
                            {turn.citations.map((citation, cIdx) => (
                              <button
                                key={cIdx}
                                onClick={() => jumpToCitation(citation)}
                                className="px-2 py-1 bg-slate-100 rounded text-[10px] font-mono text-slate-600 border border-slate-200 hover:border-indigo-400 hover:text-indigo-900 transition-colors cursor-pointer"
                              >
                                [{citation.label}]
                              </button>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions Row */}
          <div className="px-6 py-2 bg-slate-50 border-t border-slate-100 flex items-center gap-1.5 flex-wrap shrink-0" aria-label="Suggested demo queries">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider shrink-0">Suggestions:</span>
            <div className="flex flex-wrap gap-1">
              <button
                id="query-db-limit"
                onClick={() => ask(undefined, "How does the agent pipeline execute a tool call?")}
                className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded text-[10px] font-medium text-slate-600 transition-colors cursor-pointer"
              >
                Tool Call Pipeline
              </button>
              <button
                id="query-auth-jwt"
                onClick={() => ask(undefined, "Why was progressive memory loading chosen?")}
                className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded text-[10px] font-medium text-slate-600 transition-colors cursor-pointer"
              >
                Progressive Memory Choice
              </button>
              <button
                id="query-worker-redis"
                onClick={() => ask(undefined, "Is it safe to refactor ProviderAdapter?")}
                className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded text-[10px] font-medium text-slate-600 transition-colors cursor-pointer"
              >
                ProviderAdapter Refactoring
              </button>
            </div>
          </div>

          {/* Query Mode and Input composer */}
          <div className="p-4 border-t border-slate-200 bg-white shrink-0">
            <form className="relative flex flex-col md:flex-row gap-2" aria-label="Ask DevOnboard" onSubmit={(e) => ask(e)}>
              {/* Query Mode Selector */}
              <div className="flex items-center space-x-1 border border-slate-200 rounded bg-slate-50 p-1 mr-2 md:w-32 shrink-0 h-10" role="radiogroup" aria-label="Query mode">
                <button
                  type="button"
                  onClick={() => setMode("auto")}
                  className={`flex-1 text-[10px] font-medium py-1 px-1.5 rounded text-center transition-all ${
                    mode === "auto" ? "bg-white text-indigo-950 font-bold shadow-sm" : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Auto
                </button>
                <button
                  type="button"
                  onClick={() => setMode("structural")}
                  className={`flex-1 text-[10px] font-medium py-1 px-1.5 rounded text-center transition-all ${
                    mode === "structural" ? "bg-white text-indigo-950 font-bold shadow-sm" : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  Struct
                </button>
              </div>

              {/* Input box */}
              <div className="flex-1 relative flex items-center border border-slate-200 rounded-lg bg-slate-50 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:ring-offset-0 focus-within:border-transparent transition-all h-10">
                <input
                  id="query-input-field"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask about the codebase architecture or history..."
                  disabled={isAsking}
                  className="flex-grow bg-transparent px-4 py-2 text-sm outline-none disabled:opacity-50"
                />
                <button
                  id="btn-submit-query"
                  type="submit"
                  disabled={isAsking || !query.trim()}
                  className="mr-2 px-3 py-1 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-indigo-350 shrink-0 cursor-pointer transition-colors text-xs font-semibold flex items-center gap-1"
                >
                  {isAsking ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <>
                      <span>Ask</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* View Mode: Graph (Visual Three.js Graph Map View) */}
        <section id="middle-column-graph" className={`flex-1 flex flex-col bg-white overflow-hidden h-full relative ${viewMode === "graph" ? "" : "hidden"}`}>
          {graphMissing ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
              <AlertTriangle className="w-12 h-12 mb-4 text-amber-400" />
              <h2 className="font-bold text-lg text-slate-800 mb-2">No Graph Mapped</h2>
              <p className="max-w-md text-sm text-slate-500">
                Please scan the repository first to construct the semantic dependencies knowledge graph.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col h-full">
              <ArchitectureGraph
                graph={graph}
                selectedNodeId={selectedNode?.id}
                onSelectNode={selectNode}
              />
            </div>
          )}
        </section>

        {/* View Mode: Benchmark (Inline results performance metrics) */}
        <section id="middle-column-benchmark" className={`flex-grow p-6 space-y-6 max-w-7xl mx-auto w-full overflow-y-auto ${viewMode === "benchmark" ? "" : "hidden"}`} aria-label="Result dashboard">
          {/* Header Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5.5 h-5.5 text-indigo-600" />
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">DevOnboard App Result</h2>
              </div>
              <button
                id="btn-run-result"
                onClick={runResults}
                disabled={benchmarkLoading}
                className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-350 px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer transition-colors flex items-center gap-1.5"
              >
                {benchmarkLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Run Result</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-slate-500 leading-normal">
              Measure target codebase onboarding efficiency: latency, citations count, evidence coverage, and warning exceptions.
            </p>
          </div>

          {/* Results Table & Runs Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Main Stats table */}
            <div className="lg:col-span-3 bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
              <h3 className="font-semibold text-slate-800 text-sm border-b border-slate-100 pb-2">Active Run Metrics</h3>
              
              {!selectedRun ? (
                <div className="py-12 text-center text-slate-400">
                  <Award className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-xs">No result runs saved. Run a result test to collect metrics.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Visual Chart Bars */}
                  <div className="space-y-2.5" aria-label="Citation count chart">
                    {selectedRun.rows.map((row) => (
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

                  {/* Real HTML Table */}
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-100 text-xs text-left">
                      <thead>
                        <tr className="text-slate-400 font-semibold">
                          <th className="py-2 pr-4">Query</th>
                          <th className="py-2 px-4">Time</th>
                          <th className="py-2 px-4">Citations</th>
                          <th className="py-2 px-4">Evidence</th>
                          <th className="py-2 px-4">Warnings</th>
                          <th className="py-2 pl-4">Usefulness</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 text-slate-600">
                        {selectedRun.rows.map((row) => (
                          <tr key={row.query_id}>
                            <td className="py-2.5 pr-4 font-medium text-slate-800">{row.query_text}</td>
                            <td className="py-2.5 px-4 font-mono">{row.time_to_useful_answer_ms} ms</td>
                            <td className="py-2.5 px-4">{row.citations_count} citations</td>
                            <td className="py-2.5 px-4">{row.evidence_count} items</td>
                            <td className="py-2.5 px-4">{row.warnings_count}</td>
                            <td className="py-2.5 pl-4 font-mono font-bold text-indigo-600">{row.evidence_usefulness_score ?? "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Past Runs list */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col h-96">
              <h3 className="font-semibold text-slate-800 text-sm border-b border-slate-100 pb-2 mb-3">Past result runs</h3>
              <div className="flex-1 overflow-y-auto space-y-2.5">
                {benchmarkRuns.length === 0 ? (
                  <p className="text-xs text-slate-450 italic text-center py-12">No past runs saved.</p>
                ) : (
                  benchmarkRuns.map((run) => (
                    <button
                      key={run.run_id}
                      onClick={() => setSelectedRun(run)}
                      className={`w-full text-left p-3 rounded-lg border text-xs flex flex-col gap-1 transition-all cursor-pointer ${
                        selectedRun?.run_id === run.run_id
                          ? "border-indigo-500 bg-indigo-50/50 text-indigo-950 font-medium shadow-sm"
                          : "border-slate-200 hover:bg-slate-50 text-slate-600"
                      }`}
                    >
                      <strong className="font-mono block truncate">{run.run_id}</strong>
                      <span className="text-[10px] text-slate-400">{run.repo} • {run.target_branch}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

        {/* C. RIGHT COLUMN: Inspector context details */}
        <aside id="right-column" className={`w-80 border-l border-slate-200 bg-white flex flex-col shrink-0 overflow-hidden h-full ${viewMode === "benchmark" ? "hidden" : ""}`} aria-label="History and why inspector">
          <div className="p-4 border-b border-slate-100 font-semibold text-xs uppercase tracking-wider text-slate-400 shrink-0 bg-white flex items-center justify-between">
            <span>Inspector: {selectedNode ? selectedNode.name : "Codebase Detail"}</span>
            <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          </div>

          {selectedNode ? (
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              
              {/* Node Identity */}
              <div>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-tight mb-2">Item Type</h3>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="inline-block px-1.5 py-0.5 bg-indigo-100 text-indigo-800 text-[10px] font-mono font-bold uppercase rounded border border-indigo-200">
                    {selectedNode.type}
                  </span>
                  <div className="text-sm font-semibold text-slate-900 mt-2">{selectedNode.name}</div>
                  <p className="text-xs text-slate-500 mt-1">
                    {selectedNode.metadata?.description || "Source item evaluated under active codebase paths."}
                  </p>
                </div>
              </div>

              {/* Rationale design claims */}
              {selectedNode.type === "claim" && (
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-tight mb-2 font-display">AI-Extracted Rationale</h3>
                  <div className="space-y-3">
                    <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                      <div className="text-[11px] font-bold text-emerald-700 uppercase mb-1">Design Decision Impact</div>
                      <p className="text-xs text-emerald-900 leading-snug">
                        {selectedNode.metadata?.tradeoffs || "No tradeoffs document found."}
                      </p>
                    </div>

                    <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
                      <div className="text-[11px] font-bold text-amber-700 uppercase mb-1">Known Trade-off & Risk</div>
                      <p className="text-xs text-amber-950 leading-snug">
                        {selectedNode.metadata?.risks || "Associated dependency binding constraint."}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Warnings from Node History */}
              {historyEvidence.warnings && historyEvidence.warnings.length > 0 && (
                <div className="space-y-1.5">
                  {historyEvidence.warnings.map((warning, wIdx) => (
                    <div key={wIdx} className="p-2.5 bg-rose-50 border border-rose-100 text-rose-850 rounded text-xs leading-snug flex gap-1.5">
                      <AlertTriangle className="w-4 h-4 mt-0.5 text-rose-600 shrink-0" />
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Linked Commits / PRs Evidence */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-tight">Linked Commits/PRs</h3>
                {historyEvidence.evidence.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No linked commits/PRs found.</p>
                ) : (
                  <div className="space-y-2">
                    {historyEvidence.evidence.map((item) => (
                      <button
                        type="button"
                        key={`evidence-${item.node_id}`}
                        onClick={() => jumpToCitation(item)}
                        className="w-full text-left p-2.5 border border-slate-200 rounded-lg bg-slate-50 hover:bg-slate-100/50 hover:border-slate-350 transition-all flex flex-col gap-1 cursor-pointer"
                      >
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase w-fit border ${badgeClass(item.type)}`}>
                          {item.type}
                        </span>
                        <strong className="text-slate-800 text-xs block">{item.label}</strong>
                        <span className="text-[11px] text-slate-500 block line-clamp-2">{item.summary}</span>
                        {typeof item.score === "number" && item.score < 0.6 && (
                          <em className="text-[10px] text-rose-600 font-medium">Low confidence ({item.score.toFixed(2)})</em>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Claims Evidence list */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-tight">Claims</h3>
                {historyEvidence.claims.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No claims found.</p>
                ) : (
                  <div className="space-y-2">
                    {historyEvidence.claims.map((item) => (
                      <button
                        type="button"
                        key={`claim-ev-${item.node_id}`}
                        onClick={() => jumpToCitation(item)}
                        className="w-full text-left p-2.5 border border-slate-200 rounded-lg bg-slate-50 hover:bg-slate-100/50 hover:border-slate-350 transition-all flex flex-col gap-1 cursor-pointer"
                      >
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase w-fit border ${badgeClass(item.type)}`}>
                          {item.type}
                        </span>
                        <strong className="text-slate-800 text-xs block">{item.label}</strong>
                        <span className="text-[11px] text-slate-500 block line-clamp-2">{item.summary}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Risks Evidence list */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-tight">Risks</h3>
                {historyEvidence.risks.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No risks found.</p>
                ) : (
                  <div className="space-y-2">
                    {historyEvidence.risks.map((item) => (
                      <button
                        type="button"
                        key={`risk-ev-${item.node_id}`}
                        onClick={() => jumpToCitation(item)}
                        className="w-full text-left p-2.5 border border-slate-200 rounded-lg bg-slate-50 hover:bg-slate-100/50 hover:border-slate-350 transition-all flex flex-col gap-1 cursor-pointer"
                      >
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase w-fit border ${badgeClass(item.type)}`}>
                          {item.type}
                        </span>
                        <strong className="text-slate-800 text-xs block">{item.label}</strong>
                        <span className="text-[11px] text-slate-500 block line-clamp-2">{item.summary}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Button: Generate Evidence Pack */}
              <button
                type="button"
                id="btn-inspector-evidence-pack"
                onClick={() => generatePack()}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-xs transition-colors cursor-pointer shadow-sm flex items-center justify-center gap-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Generate Evidence Pack</span>
              </button>

            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-400">
              <HelpCircle className="w-8 h-8 mb-2 text-slate-300 stroke-1" />
              <p className="text-xs leading-normal">
                Click any design claim, scanned file, or member on the left panel to inspect authors, changes, and tradeoffs.
              </p>
            </div>
          )}
        </aside>

      </main>

      {/* 3. Evidence Pack Modal Panel */}
      {isPackOpen && (
        <aside className="fixed inset-y-0 right-0 w-96 border-l border-slate-200 bg-white shadow-xl flex flex-col z-50 animate-slideOver" aria-label="Evidence Pack">
          <div className="p-4 border-b border-slate-100 font-semibold text-xs uppercase tracking-wider text-slate-400 shrink-0 bg-white flex items-center justify-between">
            <strong>Evidence Pack</strong>
            <button
              type="button"
              aria-label="Close evidence pack"
              onClick={() => setIsPackOpen(false)}
              className="text-slate-400 hover:text-slate-700 text-lg cursor-pointer"
            >
              ×
            </button>
          </div>

          <div className="p-3 bg-slate-50 border-b border-slate-100 flex gap-1 shrink-0" role="radiogroup" aria-label="Evidence pack purpose">
            <button
              type="button"
              onClick={() => { setPackPurpose("pr_review"); generatePack("pr_review"); }}
              className={`flex-1 text-[10px] py-1 px-2 rounded font-semibold text-center transition-all ${
                packPurpose === "pr_review" ? "bg-white text-indigo-950 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              PR Review
            </button>
            <button
              type="button"
              onClick={() => { setPackPurpose("ai_agent_context"); generatePack("ai_agent_context"); }}
              className={`flex-1 text-[10px] py-1 px-2 rounded font-semibold text-center transition-all ${
                packPurpose === "ai_agent_context" ? "bg-white text-indigo-950 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              AI-Agent Context
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {isGeneratingPack ? (
              <div className="space-y-3 animate-pulse" aria-label="Generating evidence pack">
                <div className="h-4 bg-slate-100 rounded w-3/4"></div>
                <div className="h-24 bg-slate-100 rounded"></div>
                <div className="h-4 bg-slate-100 rounded w-1/2"></div>
              </div>
            ) : pack ? (
              <>
                {pack.evidence_only && (
                  <div className="p-2.5 bg-rose-50 border border-rose-100 text-rose-900 rounded text-xs">
                    Generated without external LLM. Evidence-only export.
                  </div>
                )}
                {pack.warnings.map((warning, wIdx) => (
                  <div key={wIdx} className="p-2.5 bg-amber-50 border border-amber-100 text-amber-900 rounded text-xs flex gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    <span>{warning}</span>
                  </div>
                ))}
                {pack.excluded_sources.length > 0 && (
                  <div className="p-2 bg-slate-100 border border-slate-200 text-slate-650 rounded text-xs">
                    {pack.excluded_sources.length} sources excluded from AI context.
                  </div>
                )}

                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Markdown Preview</span>
                  <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[10.5px] font-mono overflow-auto max-h-60 leading-relaxed border border-slate-950">
                    {pack.markdown}
                  </pre>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Citations</span>
                  {pack.citations.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No citations in this pack.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {pack.citations.map((c) => (
                        <div key={c.node_id} className="p-2 bg-slate-50 border border-slate-200 rounded text-[11px] font-mono flex items-center justify-between">
                          <span className="font-semibold text-slate-700 truncate">[{c.label}]</span>
                          <span className="text-[9px] uppercase font-bold text-slate-450 border border-slate-200 px-1 rounded bg-white">{c.type}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400 italic text-center py-12">
                Generate an evidence pack to preview copyable Markdown.
              </p>
            )}
          </div>

          <div className="p-4 border-t border-slate-100 bg-slate-50 flex gap-2 shrink-0">
            <button
              type="button"
              onClick={copyPack}
              disabled={!pack || isGeneratingPack}
              className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-lg text-xs transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <ClipboardCopy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </button>
            <button
              type="button"
              onClick={exportPack}
              disabled={!pack || isGeneratingPack}
              className="flex-1 py-2 bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-50 text-slate-700 font-semibold rounded-lg text-xs transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
          </div>
          {copyState && (
            <p className="px-4 py-1.5 bg-emerald-50 text-emerald-800 border-t border-emerald-100 text-center text-xs font-semibold shrink-0">
              {copyState}
            </p>
          )}
        </aside>
      )}

      {/* 4. Footer */}
      <footer className="h-10 bg-white border-t border-slate-200 px-6 shrink-0 flex items-center justify-between text-xs text-slate-400">
        <div>DevOnboard Architecture Indexer</div>
        <div className="flex items-center space-x-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>Sync engine ready</span>
        </div>
      </footer>

    </div>
  );
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, init);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error?.message || payload?.detail || `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return payload as T;
}

async function pollJobStatus(
  path: string,
  onStatus: (status: JobStatus) => void,
): Promise<JobStatus> {
  const deadline = Date.now() + jobPollTimeoutMs;

  while (Date.now() < deadline) {
    const status = await requestJson<JobStatus>(path);
    onStatus(status);

    if (status.status === "done" || status.status === "error") {
      return status;
    }

    await wait(jobPollIntervalMs);
  }

  throw new Error("Scan timed out while waiting for backend status.");
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

function safeStorageGet(key: string) {
  if (typeof window === "undefined" || !window.localStorage) return null;
  return window.localStorage.getItem(key);
}

function safeStorageSet(key: string, value: string) {
  if (typeof window === "undefined" || !window.localStorage) return;
  window.localStorage.setItem(key, value);
}
