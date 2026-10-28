import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "Smart Guardian | Digital Oilfield & Reservoir Intelligence",
  description: "Production-grade digital oilfield and reservoir-engineering intelligence platform with real-time surveillance, field integration, and decision support.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased bg-[#050507] text-white min-h-screen selection:bg-red-600/30 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
