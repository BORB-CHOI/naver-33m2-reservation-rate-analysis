import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      {/* suppressHydrationWarning로 서버‧클라이언트 DOM 불일치 경고 최소화 */}
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
