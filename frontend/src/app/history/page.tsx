"use client";

import { useEffect, useState } from "react";
import { Clock, ShieldCheck } from "lucide-react";
import { getRiskLabel, getRiskColor } from "@/lib/utils";
import type { AnalysisStatus } from "@/types";

// Note: For MVP, the history is stored client-side in localStorage.
// In production, this would be fetched from a user-authenticated API endpoint.

interface HistoryEntry {
  taskId: string;
  filename: string;
  timestamp: string;
  overallRisk: string;
}

const HISTORY_KEY = "licenselight-history";

function getStoredHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setHistory(getStoredHistory());
  }, []);

  const clearHistory = () => {
    localStorage.removeItem(HISTORY_KEY);
    setHistory([]);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">历史记录</h1>
          <p className="text-muted-foreground">
            查看之前的图片版权检测结果
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            className="px-4 py-2 text-sm border rounded-lg text-red-500 hover:bg-red-50 transition-colors"
          >
            清空记录
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="text-center py-20">
          <Clock className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-semibold mb-2 text-muted-foreground">
            暂无历史记录
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            上传并分析图片后，记录将显示在这里
          </p>
          <a
            href="/"
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-block"
          >
            开始检测
          </a>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((entry) => (
            <a
              key={entry.taskId}
              href={`/results/${entry.taskId}`}
              className="block bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="font-semibold">{entry.filename}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(entry.timestamp).toLocaleString("zh-CN")}
                    </p>
                  </div>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${getRiskColor(entry.overallRisk)}`}
                >
                  {getRiskLabel(entry.overallRisk)}
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
