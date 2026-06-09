import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LicenseLight - 版权合规助手",
  description:
    "面向设计师和独立开发者的版权合规副驾驶。上传设计图片，一键检测字体和图片来源的版权风险。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
          {/* Header */}
          <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
            <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <span className="text-white font-bold text-sm">LL</span>
                </div>
                <span className="font-bold text-xl tracking-tight">
                  License<span className="text-blue-500">Light</span>
                </span>
              </a>
              <nav className="flex items-center gap-6 text-sm text-muted-foreground">
                <a href="/" className="hover:text-foreground transition-colors">
                  首页
                </a>
                <a
                  href="/history"
                  className="hover:text-foreground transition-colors"
                >
                  历史记录
                </a>
              </nav>
            </div>
          </header>

          {/* Main Content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="border-t py-8 mt-20">
            <div className="max-w-5xl mx-auto px-4 text-center text-sm text-muted-foreground">
              <p>
                LicenseLight &copy; {new Date().getFullYear()} — 版权合规副驾驶，
                为你的创作保驾护航。
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
