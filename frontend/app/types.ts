export enum NodeType {
  FILE = "file",
  MODULE = "module",
  FUNCTION = "function",
  CLASS = "class",
  SERVICE = "service",
  ENDPOINT = "endpoint",
  CONFIG = "config",
  DOMAIN = "domain",
  FLOW = "flow",
  STEP = "step",
  SOURCE = "source",
  CLAIM = "claim",
  ENTITY = "entity",
  TOPIC = "topic"
}

export enum EdgeType {
  CONTAINS = "contains",
  IMPORTS = "imports",
  CALLS = "calls",
  DEPENDS_ON = "depends_on",
  IMPLEMENTS = "implements",
  ROUTES = "routes",
  CONFIGURES = "configures",
  DOCUMENTS = "documents",
  AUTHORED_BY = "authored_by",
  EXEMPLIFIES = "exemplifies",
  CITES = "cites",
  BUILDS_ON = "builds_on",
  CONTRADICTS = "contradicts"
}

export interface GraphNode {
  id: string;
  type: NodeType | string;
  name: string;
  metadata?: {
    path?: string;
    lineStart?: number;
    lineEnd?: number;
    description?: string;
    // for claims (tradeoffs, rejected alternatives, refactor risks)
    tradeoffs?: string;
    rejectedAlternatives?: string;
    risks?: string;
    // for sources (commits/PRs)
    hash?: string;
    author?: string;
    date?: string;
    filesTouched?: string[];
    // for entities (authors/reviewers/libs)
    role?: string;
    [key: string]: any;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  type: EdgeType;
  metadata?: Record<string, any>;
}

export interface KnowledgeGraph {
  version?: string;
  generated_at?: string;
  repo?: {
    name: string;
    path?: string;
    branch: string;
    commit?: string | null;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: {
    nodeId: string;
    name: string;
    type: NodeType;
    summary: string;
  }[];
}

export interface BenchmarkResult {
  query: string;
  system: "DevOnboard (Graph RAG)" | "Plain LLM (No Graph)";
  response: string;
  timeMs: number;
  accuracy: number; // 1-5 scale or percentage
  completeness: number; // 1-5 scale
  relevance: number; // 1-5 scale
  citationsCount: number;
}
