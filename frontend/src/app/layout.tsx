import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const cairo = Cairo({
  subsets: ["arabic", "latin"],
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  variable: "--font-cairo",
  display: "swap",
});

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
    <html lang="en" dir="ltr" className={`${cairo.variable}`}>
      <body className="antialiased bg-[#070b13] text-slate-100 min-h-screen font-cairo selection:bg-cyan-500/20 selection:text-cyan-300">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
