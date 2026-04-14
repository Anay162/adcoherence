import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AdCoherence — Free Google Ads Audit Tool",
  description:
    "Instantly audit how well your Google Ads copy matches your landing pages. Discover wasted spend and get specific fixes.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
