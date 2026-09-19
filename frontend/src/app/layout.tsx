import type { Metadata } from "next";
import SiteFooter from "@/components/SiteFooter";
import "./globals.css";

export const metadata: Metadata = {
  title: "Advoxy | On-demand hair and nail services",
  description:
    "Book verified independent hair and nail professionals for at-home, office, hotel, or senior-home appointments in Calgary.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased" data-scroll-behavior="smooth">
      <body className="min-h-full flex flex-col">{children}<SiteFooter /></body>
    </html>
  );
}
