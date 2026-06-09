"use client";

import { useState, useCallback, useEffect } from "react";
import { Upload, Loader2, ShieldCheck, AlertTriangle, CheckCircle } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { uploadImage, pollAnalysisStatus } from "@/lib/api";
import { getSettings } from "@/lib/settings";
import { SettingsPanel } from "@/components/SettingsPanel";
import {
  getRiskLabel,
  getRiskBadgeClass,
  getRiskPillColor,
  getRiskBorderColor,
  getRiskDotClass,
} from "@/lib/utils";
import type { AnalysisStatus, AnalysisReport, UserSettings } from "@/types";

export default function HomePage() {
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userSettings, setUserSettings] = useState<UserSettings | null>(null);

  // Load saved settings from localStorage on mount
  useEffect(() => {
    setUserSettings(getSettings());
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setIsUploading(true);
    setError(null);
    setReport(null);
    setProgress(0);

    try {
      const currentSettings = getSettings();
      const uploadRes = await uploadImage(
        file,
        currentSettings?.apiKey,
        currentSettings?.aiProvider,
      );
      setTaskId(uploadRes.task_id);
      setStatus("processing");

      // Simulate progress while polling
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          const increment = prev < 60 ? 3 : prev < 85 ? 1 : 0.5;
          return Math.min(prev + increment, 90);
        });
      }, 1000);

      pollAnalysisStatus(
        uploadRes.task_id,
        (statusUpdate: AnalysisStatus) => {
          setStatus(statusUpdate.status);
        },
        (finalStatus: AnalysisStatus) => {
          clearInterval(progressInterval);
          setProgress(100);
          setStatus(finalStatus.status);

          if (finalStatus.status === "completed" && finalStatus.result) {
            setReport(finalStatus.result);
          } else if (finalStatus.status === "failed") {
            setError(finalStatus.error_message || "分析失败，请重试。");
          }
          setIsUploading(false);
        },
        (err: Error) => {
          clearInterval(progressInterval);
          setError(err.message);
          setIsUploading(false);
          setStatus("failed");
        }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
      setIsUploading(false);
      setStatus("failed");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
      "image/gif": [".gif"],
      "image/bmp": [".bmp"],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
    disabled: isUploading,
  });

  const resetAnalysis = () => {
    setTaskId(null);
    setStatus(null);
    setProgress(0);
    setReport(null);
    setError(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      {/* Hero Section */}
      {!status && (
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 text-blue-700 text-sm mb-6">
            <ShieldCheck className="w-4 h-4" />
            版权合规副驾驶
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            你的设计，版权无忧
          </h1>
          <p className="text-lg text-muted-foreground max-w-lg mx-auto">
            上传一张设计图片，LicenseLight
            将自动检测字体授权和图片来源风险，
            给出清晰的红绿灯合规报告。
          </p>
        </div>
      )}

      {/* Settings Row */}
      {!taskId && (
        <div className="flex justify-end mb-4">
          <SettingsPanel
            onSettingsChange={(s) => setUserSettings(s)}
            disabled={isUploading}
          />
        </div>
      )}

      {/* Upload Zone */}
      {!taskId && (
        <div
          {...getRootProps()}
          className={`
            relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
            transition-all duration-200
            ${
              isDragActive
                ? "border-blue-400 bg-blue-50 scale-[1.02]"
                : "border-gray-300 hover:border-blue-300 hover:bg-gray-50"
            }
            ${isUploading ? "opacity-50 pointer-events-none" : ""}
          `}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold mb-2">
            {isDragActive ? "松开以上传图片" : "拖放图片到此处，或点击选择"}
          </h3>
          <p className="text-sm text-muted-foreground">
            支持 JPG、PNG、WebP、GIF、BMP 格式，最大 20MB
          </p>
        </div>
      )}

      {/* Progress */}
      {isUploading && (
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 mx-auto mb-6 animate-spin text-blue-500" />
          <h3 className="text-lg font-semibold mb-4">正在分析中...</h3>
          <div className="max-w-md mx-auto">
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              正在进行 OCR 识别、字体检测、图片来源溯源...
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-center py-12">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <h3 className="text-lg font-semibold mb-2 text-red-600">分析失败</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button
            onClick={resetAnalysis}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            重新上传
          </button>
        </div>
      )}

      {/* Results */}
      {report && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
          {/* Overall Risk Badge */}
          <div className="text-center sticky top-20 z-10">
            <div
              className={`
                inline-flex items-center gap-3 px-6 py-3 rounded-full shadow-md
                ${getRiskBadgeClass(report.overall_risk)}
              `}
            >
              <div className={`w-3 h-3 rounded-full ${getRiskDotClass(report.overall_risk)}`} />
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

          {/* Font Results */}
          {report.fonts.length > 0 && (
            <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h2 className="text-lg font-bold">字体授权检测</h2>
                <p className="text-sm text-muted-foreground">
                  共检测到 {report.fonts.length} 个字体
                </p>
              </div>
              <div className="divide-y">
                {report.fonts.map((font, i) => (
                  <div
                    key={i}
                    className={`px-6 py-5 border-l-4 ${getRiskBorderColor(font.risk)}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-bold text-lg">{font.name}</h3>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getRiskPillColor(font.risk)}`}
                          >
                            {getRiskLabel(font.risk)}
                          </span>
                        </div>
                        <p className="text-muted-foreground text-sm">
                          {font.explanation}
                        </p>
                        {font.detected_text && font.detected_text.length > 0 && (
                          <div className="mt-2">
                            <span className="text-xs font-semibold text-gray-500">
                              检测到的文字：
                            </span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {font.detected_text.slice(0, 8).map((text, j) => (
                                <span
                                  key={j}
                                  className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-mono"
                                >
                                  {text}
                                </span>
                              ))}
                              {font.detected_text.length > 8 && (
                                <span className="text-xs text-gray-400 self-center">
                                  +{font.detected_text.length - 8} 更多
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        {font.alternatives.length > 0 && (
                          <div className="mt-3">
                            <span className="text-xs font-semibold text-green-600">
                              推荐替代字体：
                            </span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {font.alternatives.map((alt, j) => (
                                <span
                                  key={j}
                                  className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs"
                                >
                                  {alt}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Image Source Result */}
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
                      className="text-sm text-blue-500 hover:underline truncate max-w-md"
                    >
                      {report.image_source.source_url}
                    </a>
                  )}
                </div>
                <p className="text-muted-foreground text-sm">
                  {report.image_source.explanation}
                </p>
                {report.image_source.alternatives.length > 0 && (
                  <div className="mt-3">
                    <span className="text-xs font-semibold text-green-600">
                      推荐替代图库：
                    </span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {report.image_source.alternatives.map((alt, j) => (
                        <a
                          key={j}
                          href={alt}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs hover:underline"
                        >
                          {alt}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Reset Button */}
          <div className="text-center pt-4">
            <button
              onClick={resetAnalysis}
              className="px-6 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              检测新图片
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
