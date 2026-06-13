import { render, screen } from "@testing-library/react";
import ResultsPage from "./page";

describe("ResultsPage", () => {
  it("renders app result controls without agent comparison copy", () => {
    render(<ResultsPage />);

    expect(screen.getByLabelText("Result dashboard")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Run Result/i }).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /DevOnboard App Result/i })).toBeInTheDocument();
    expect(screen.getByText(/Past result runs/i)).toBeInTheDocument();
    expect(screen.queryByText(/plain-agent/i)).not.toBeInTheDocument();
  });
});
