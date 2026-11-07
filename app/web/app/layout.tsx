import type { Metadata, Viewport } from "next";
import { ScrollbarReveal } from "@/components/ScrollbarReveal";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ridgeback fleet",
  description: "How Ridgeback Logistics' machines and drivers performed, with a chat assistant.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// Applies a saved theme before first paint, so the page doesn't flash the wrong one.
const themeScript = `try{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-ZA" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-dvh antialiased">
        <ScrollbarReveal />
        {children}
      </body>
    </html>
  );
}
