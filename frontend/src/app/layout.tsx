import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "CodeRazz — Misconception-Aware Programming Tutor",
  description:
    "Don't just fix the code. Understand the thinking behind it. CodeRazz diagnoses underlying mental model errors and guides learners with progressive hints.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-slate-950 text-slate-100 min-h-screen flex flex-col bg-grid-pattern">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
          <p>
            CodeRazz © 2026 — 100% Free & Open-Source. Built with Next.js 15, FastAPI, and PostgreSQL 16.
          </p>
        </footer>
      </body>
    </html>
  );
}

