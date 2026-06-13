import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("opens directly into the DevOnboard workspace", () => {
    render(<Home />);

    expect(screen.getByLabelText("DevOnboard workspace")).toBeInTheDocument();
    expect(screen.getByLabelText("Cited question and answer thread")).toBeInTheDocument();
    expect(screen.getByLabelText("History and why inspector")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run Scan/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ingest History/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Ask$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate Evidence Pack/i })).toBeInTheDocument();
  });
});
