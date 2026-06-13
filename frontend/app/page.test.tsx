import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("opens directly into the DevOnboard workspace", () => {
    render(<Home />);

    expect(screen.getByLabelText("DevOnboard workspace")).toBeInTheDocument();
    expect(screen.getByLabelText("Cited question and answer thread")).toBeInTheDocument();
    expect(screen.getByLabelText("History and why inspector")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ProviderAdapter/i })).toBeInTheDocument();
  });
});
