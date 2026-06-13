import { render, screen } from "@testing-library/react";
import BenchmarkPage from "./page";

describe("BenchmarkPage", () => {
  it("renders the benchmark dashboard controls and comparison surface", () => {
    render(<BenchmarkPage />);

    expect(screen.getByLabelText("Benchmark dashboard")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Run Benchmark/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /DevOnboard vs plain-agent/i })).toBeInTheDocument();
    expect(screen.getByText(/Past runs/i)).toBeInTheDocument();
  });
});
