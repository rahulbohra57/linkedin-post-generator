import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LinkedIn Post Generator — Agentic AI",
  description: "Generate and publish high-quality LinkedIn posts with AI agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen">
          <header className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="max-w-4xl mx-auto flex items-center gap-3">
              <div className="w-8 h-8 bg-linkedin-blue rounded flex items-center justify-center">
                <span className="text-white font-bold text-sm">in</span>
              </div>
              <h1 className="text-lg font-semibold text-gray-900">
                LinkedIn Post Generator
              </h1>
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                Powered by Agentic AI
              </span>
            </div>
          </header>
          <main className="max-w-4xl mx-auto px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
