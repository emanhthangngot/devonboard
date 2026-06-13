import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "DevOnboard",
  description: "Local codebase institutional memory with cited evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
