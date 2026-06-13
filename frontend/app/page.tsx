import { Activity, GitBranch, Search } from "lucide-react";

const demoQueries = [
  "How does the agent pipeline execute a tool call?",
  "Why was progressive memory loading chosen?",
  "Is it safe to refactor ProviderAdapter?",
];

export default function Home() {
  return (
    <main className="app-shell" aria-label="DevOnboard workspace">
      <nav className="top-nav" aria-label="Workspace status">
        <div className="repo-chip">
          <GitBranch size={16} aria-hidden="true" />
          <span>nextlevelbuilder/goclaw</span>
          <code>dev</code>
        </div>
        <div className="status-group">
          <span className="status-pill">Scan idle</span>
          <span className="status-pill">Ingest idle</span>
          <a href="/benchmark">Benchmark</a>
        </div>
      </nav>

      <section className="workspace-grid">
        <aside className="left-panel" aria-label="Graph and file navigation">
          <div className="panel-header">
            <span>Files</span>
            <Search size={14} aria-hidden="true" />
          </div>
          <p className="empty-copy">No graph found. Run Scan to populate the navigator.</p>
        </aside>

        <section className="chat-panel" aria-label="Cited question and answer thread">
          <div className="thread">
            <div className="assistant-intro">
              <Activity size={18} aria-hidden="true" />
              <div>
                <h1>Ask about code history with citations.</h1>
                <p>
                  DevOnboard answers structural, historical, and refactor-risk questions
                  from the local graph and linked evidence.
                </p>
              </div>
            </div>

            <div className="suggestions" aria-label="Suggested demo queries">
              {demoQueries.map((query) => (
                <button key={query} type="button">
                  {query}
                </button>
              ))}
            </div>
          </div>

          <form className="composer" aria-label="Ask DevOnboard">
            <label htmlFor="query">Query</label>
            <textarea id="query" placeholder="Ask a cited question about this repo..." rows={2} />
            <button type="submit">Ask</button>
          </form>
        </section>

        <aside className="right-panel" aria-label="History and why inspector">
          <div className="panel-header">
            <span>History / Why</span>
          </div>
          <p className="empty-copy">
            Select a file, function, or module to see its History/Why context.
          </p>
        </aside>
      </section>
    </main>
  );
}
