"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { getAnalysisStatus } from "@/lib/api";
import {
  getRiskLabel,
  getRiskBadgeClass,
  getRiskPillColor,
  getRiskBorderColor,
  getRiskDotClass,
} from "@/lib/utils";
import type { AnalysisReport } from "@/types";

export default function ResultsPage() {
  const params = useParams();
  const taskId = params.taskId as string;
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      while (!cancelled) {
        try {
          const status = await getAnalysisStatus(taskId);

          if (status.status === "completed" && status.result) {
            if (!cancelled) {
              setReport(status.result);
              setLoading(false);
            }
            return;
          }

          if (status.status === "failed") {
            if (!cancelled) {
              setError(status.error_message || "分析失败");
              setLoading(false);
            }
            return;
          }
        } catch (err) {
          if (!cancelled) {
            setError("获取结果失败");
            setLoading(false);
          }
          return;
        }

        await new Promise((r) => setTimeout(r, 2000));
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [taskId]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <Loader2 className="w-12 h-12 mx-auto mb-6 animate-spin text-blue-500" />
        <h3 className="text-lg font-semibold mb-2">正在加载分析结果...</h3>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <p className="text-red-500 mb-4">{error || "结果不存在"}</p>
        <a href="/" className="text-blue-500 hover:underline">
          返回首页
        </a>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12 space-y-8">
      {/* Overall Risk */}
      <div className="text-center">
        <div
          className={`inline-flex items-center gap-3 px-6 py-3 rounded-full shadow-md ${getRiskBadgeClass(report.overall_risk)}`}
        >
          <div className={`w-4 h-4 rounded-full ${getRiskDotClass(report.overall_risk)}`} />
          <span className="text-lg font-bold">
            综合风险：{getRiskLabel(report.overall_risk)}
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white rounded-2xl border p-6 shadow-sm">
        <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-500" />
          检测总结
        </h2>
        <p className="text-muted-foreground leading-relaxed whitespace-pre-line">
          {report.summary}
        </p>
      </div>

      {/* Fonts */}
      {report.fonts.length > 0 && (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h2 className="text-lg font-bold">字体授权检测</h2>
          </div>
          <div className="divide-y">
            {report.fonts.map((font, i) => (
              <div
                key={i}
                className={`px-6 py-5 border-l-4 ${getRiskBorderColor(font.risk)}`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-bold text-lg">{font.name}</h3>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getRiskPillColor(font.risk)}`}
                  >
                    {getRiskLabel(font.risk)}
                  </span>
                </div>
                <p className="text-muted-foreground text-sm">{font.explanation}</p>
                {font.alternatives.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {font.alternatives.map((alt, j) => (
                      <span
                        key={j}
                        className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs"
                      >
                        {alt}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Image Source */}
      {report.image_source && (
        <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h2 className="text-lg font-bold">图片来源检测</h2>
          </div>
          <div
            className={`px-6 py-5 border-l-4 ${getRiskBorderColor(report.image_source.risk)}`}
          >
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getRiskPillColor(report.image_source.risk)}`}
              >
                {getRiskLabel(report.image_source.risk)}
              </span>
              {report.image_source.source_url && (
                <a
                  href={report.image_source.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-500 hover:underline truncate"
                >
                  {report.image_source.source_url}
                </a>
              )}
            </div>
            <p className="text-muted-foreground text-sm">
              {report.image_source.explanation}
            </p>
          </div>
        </div>
      )}

      <div className="text-center pt-4">
        <a href="/" className="px-6 py-2 border rounded-lg hover:bg-gray-50 transition-colors inline-block">
          检测新图片
        </a>
      </div>
    </div>
  );
}
