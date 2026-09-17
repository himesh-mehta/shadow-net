import type { Metadata } from "next";
import { AuthProvider } from "@/lib/authContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "SHADOW-NET | SOC Deepfake Interception Prototype",
  description: "Real-time acoustic analysis, deepfake voice detection, and proactive session response in controlled testing environments.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen bg-[#070a13] text-slate-100 selection:bg-cyan-500/20 selection:text-cyan-300">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
