import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHADOW-NET | Deepfake Voice Interception Prototype",
  description: "Real-time acoustic analysis, deepfake voice detection, and proactive session response in controlled testing environments.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#0a0d14] text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
        {children}
      </body>
    </html>
  );
}
