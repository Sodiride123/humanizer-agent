import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Humanizer — AI Content Detector",
  description: "Detect AI-generated content with sentence-level analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}