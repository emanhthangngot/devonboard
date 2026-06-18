import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  beforeEach(() => {
    window.localStorage?.clear();
    vi.restoreAllMocks();
    vi.spyOn(global, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return Response.json({
          status: "ok",
          graph_exists: false,
          target_repo: { path: "./target_repo", branch: "dev", commit: null },
        });
      }
      if (url.endsWith("/scan") && init?.method === "POST") {
        return Response.json({ status: "done", progress: 100 }, { status: 202 });
      }
      if (url.endsWith("/ingest/history") && init?.method === "POST") {
        return Response.json({ status: "done", progress: 100 }, { status: 202 });
      }
      if (url.endsWith("/graph")) {
        return Response.json({ version: "0.1.0", repo: { name: "demo", path: "./target_repo", branch: "dev" }, nodes: [], edges: [] });
      }
      return Response.json({});
    });
  });

  it("opens directly into the DevOnboard workspace", () => {
    render(<Home />);

    expect(screen.getByLabelText("DevOnboard workspace")).toBeInTheDocument();
    expect(screen.getByLabelText("Cited question and answer thread")).toBeInTheDocument();
    expect(screen.getByLabelText("History and why inspector")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Run Scan/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Ingest History/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Ask$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate Evidence Pack/i })).toBeInTheDocument();
  });

  it("uses the selected repo path or GitHub URL for scan and history ingest", async () => {
    const fetchMock = vi.mocked(global.fetch);
    render(<Home />);

    const repoInput = (await screen.findAllByLabelText("Repository path or GitHub URL"))[0];
    fireEvent.change(repoInput, { target: { value: "https://github.com/nextlevelbuilder/goclaw" } });
    fireEvent.click(screen.getAllByRole("button", { name: /Run Scan/i })[0]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/scan",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("https://github.com/nextlevelbuilder/goclaw"),
        }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /Ingest History/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/ingest/history",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("https://github.com/nextlevelbuilder/goclaw"),
        }),
      );
    });
  });

  it("waits for scan status to finish before loading the graph", async () => {
    let graphRequests = 0;
    let graphRequestedBeforeDone = false;
    let statusRequests = 0;
    vi.mocked(global.fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return Response.json({
          status: "ok",
          graph_exists: false,
          target_repo: { path: "./target_repo", branch: "dev", commit: null },
        });
      }
      if (url.endsWith("/scan") && init?.method === "POST") {
        return Response.json({ status: "running", progress: 10 }, { status: 202 });
      }
      if (url.endsWith("/scan/status")) {
        statusRequests += 1;
        return Response.json(
          statusRequests === 1
            ? { status: "running", progress: 40, message: "Scanning" }
            : { status: "done", progress: 100, message: "Scanned 2 nodes and 1 edges." },
        );
      }
      if (url.endsWith("/graph")) {
        graphRequests += 1;
        if (statusRequests < 2) graphRequestedBeforeDone = true;
        return Response.json({
          version: "0.1.0",
          repo: { name: "demo", path: "./target_repo", branch: "dev" },
          nodes: [{ id: "file:main.go", type: "file", name: "main.go", summary: "Go source file main.go.", tags: ["file"], filePath: "main.go" }],
          edges: [],
        });
      }
      if (url.includes("/graph/node/")) {
        return Response.json({ evidence: [], claims: [], risks: [], warnings: [] });
      }
      return Response.json({});
    });

    render(<Home />);

    fireEvent.click(screen.getAllByRole("button", { name: /Run Scan/i })[0]);

    await waitFor(() => expect(statusRequests).toBeGreaterThanOrEqual(2));
    expect(graphRequestedBeforeDone).toBe(false);
    await waitFor(() => expect(graphRequests).toBeGreaterThanOrEqual(1));
    expect(await screen.findByRole("button", { name: "main.go" })).toBeInTheDocument();
  });

  it("surfaces scan status errors without loading a stale graph", async () => {
    let graphRequests = 0;
    vi.mocked(global.fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return Response.json({
          status: "ok",
          graph_exists: false,
          target_repo: { path: "./target_repo", branch: "dev", commit: null },
        });
      }
      if (url.endsWith("/scan") && init?.method === "POST") {
        return Response.json({ status: "running", progress: 10 }, { status: 202 });
      }
      if (url.endsWith("/scan/status")) {
        return Response.json({ status: "error", progress: 0, error: "Repository path does not exist: /missing" });
      }
      if (url.endsWith("/graph")) {
        graphRequests += 1;
        return Response.json({ version: "0.1.0", repo: { name: "old", path: "./old", branch: "dev" }, nodes: [], edges: [] });
      }
      return Response.json({});
    });

    render(<Home />);

    fireEvent.click(screen.getAllByRole("button", { name: /Run Scan/i })[0]);

    expect(await screen.findByText("Repository path does not exist: /missing")).toBeInTheDocument();
    expect(graphRequests).toBe(0);
  });

  it("waits for ingest status to finish before loading the graph", async () => {
    let graphRequests = 0;
    let graphRequestedBeforeDone = false;
    let statusRequests = 0;
    vi.mocked(global.fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return Response.json({
          status: "ok",
          graph_exists: false,
          target_repo: { path: "./target_repo", branch: "dev", commit: null },
        });
      }
      if (url.endsWith("/ingest/history") && init?.method === "POST") {
        return Response.json({ status: "running", progress: 10 }, { status: 202 });
      }
      if (url.endsWith("/ingest/history/status")) {
        statusRequests += 1;
        return Response.json(
          statusRequests === 1
            ? { status: "running", progress: 40, message: "Ingesting history" }
            : { status: "done", progress: 100, message: "Ingested history." },
        );
      }
      if (url.endsWith("/graph")) {
        graphRequests += 1;
        if (statusRequests < 2) graphRequestedBeforeDone = true;
        return Response.json({
          version: "0.1.0",
          repo: { name: "demo", path: "./target_repo", branch: "dev" },
          nodes: [{ id: "file:main.go", type: "file", name: "main.go", summary: "Go source file main.go.", tags: ["file"], filePath: "main.go" }],
          edges: [],
        });
      }
      if (url.includes("/graph/node/")) {
        return Response.json({ evidence: [], claims: [], risks: [], warnings: [] });
      }
      return Response.json({});
    });

    render(<Home />);

    fireEvent.click(screen.getByRole("button", { name: /Ingest History/i }));

    await waitFor(() => expect(statusRequests).toBeGreaterThanOrEqual(2));
    expect(graphRequestedBeforeDone).toBe(false);
    await waitFor(() => expect(graphRequests).toBeGreaterThanOrEqual(1));
  });
});
