import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "1Q Lecture Script Matcher",
  description: "AI가 알아서 정리해주는 강의록 위의 스크립트",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
