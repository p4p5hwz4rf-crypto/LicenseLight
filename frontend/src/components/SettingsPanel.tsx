"use client";

import { useState, useEffect } from "react";
import { Settings, Key, Eye, EyeOff, CheckCircle2, X, AlertCircle } from "lucide-react";
import {
  getSettings,
  saveSettings,
  clearSettings,
  maskApiKey,
  getProviderLabel,
  providerHasVision,
} from "@/lib/settings";
import type { AIProvider, UserSettings } from "@/types";

const PROVIDERS: { value: AIProvider; label: string; hasVision: boolean }[] = [
  { value: "claude", label: "Claude", hasVision: true },
  { value: "openai", label: "OpenAI", hasVision: true },
  { value: "gemini", label: "Gemini", hasVision: true },
  { value: "kimi", label: "Kimi", hasVision: true },
  { value: "deepseek", label: "DeepSeek", hasVision: false },
];

interface SettingsPanelProps {
  onSettingsChange: (settings: UserSettings | null) => void;
  disabled?: boolean;
}

export function SettingsPanel({ onSettingsChange, disabled }: SettingsPanelProps) {
  const [open, setOpen] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [provider, setProvider] = useState<AIProvider>("claude");
  const [apiKey, setApiKey] = useState("");
  const [saved, setSaved] = useState<UserSettings | null>(null);

  // Load saved settings on mount
  useEffect(() => {
    const existing = getSettings();
    if (existing) {
      setSaved(existing);
      setProvider(existing.aiProvider);
      setApiKey(existing.apiKey);
      onSettingsChange(existing);
    }
  }, []);

  const handleSave = () => {
    if (!apiKey.trim() || !provider) return;
    const settings: UserSettings = { aiProvider: provider, apiKey: apiKey.trim() };
    saveSettings(settings);
    setSaved(settings);
    onSettingsChange(settings);
    setShowKey(false);
  };

  const handleClear = () => {
    clearSettings();
    setSaved(null);
    setApiKey("");
    setProvider("claude");
    onSettingsChange(null);
  };

  const hasVision = providerHasVision(provider);

  return (
    <div className="relative">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        disabled={disabled}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
          transition-colors
          ${saved
            ? "bg-green-50 text-green-700 hover:bg-green-100 border border-green-200"
            : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200"
          }
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        `}
      >
        {saved ? (
          <CheckCircle2 className="w-4 h-4" />
        ) : (
          <Settings className="w-4 h-4" />
        )}
        {saved ? "API 已配置" : "API 设置"}
      </button>

      {/* Expandable panel */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl border shadow-xl z-50 p-4 space-y-3 animate-in slide-in-from-top-2">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Key className="w-4 h-4" />
              API 密钥设置
            </h3>
            <button
              onClick={() => setOpen(false)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className="text-xs text-muted-foreground">
            密钥仅存储在您的浏览器中，不会上传到服务器。每次分析时随图片一起发送。
          </p>

          {/* Provider selector */}
          <div>
            <label className="text-xs font-semibold text-gray-500 mb-1.5 block">
              AI 供应商
            </label>
            <div className="grid grid-cols-3 gap-1">
              {PROVIDERS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setProvider(p.value)}
                  disabled={disabled}
                  className={`
                    px-2 py-1.5 rounded text-xs font-medium transition-colors
                    ${provider === p.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }
                  `}
                >
                  {p.label}
                  {!p.hasVision && (
                    <span className="block text-[10px] opacity-70">仅文本</span>
                  )}
                </button>
              ))}
            </div>
            {!hasVision && (
              <p className="text-[11px] text-amber-600 mt-1 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                DeepSeek 不支持图片识别，无法进行字体检测
              </p>
            )}
          </div>

          {/* API key input */}
          <div>
            <label className="text-xs font-semibold text-gray-500 mb-1.5 block">
              API 密钥
            </label>
            {saved && !showKey ? (
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-gray-50 rounded text-sm font-mono text-gray-600">
                  {maskApiKey(saved.apiKey)}
                </code>
                <button
                  onClick={() => {
                    setApiKey(saved.apiKey);
                    setShowKey(true);
                  }}
                  className="p-1.5 hover:bg-gray-100 rounded text-gray-400"
                  title="显示/编辑密钥"
                >
                  <Eye className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={getProviderLabel(provider) + " API 密钥"}
                  disabled={disabled}
                  className="w-full px-3 py-2 pr-10 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded text-gray-400"
                >
                  {showKey ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSave}
              disabled={disabled || !apiKey.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              保存
            </button>
            {saved && (
              <button
                onClick={handleClear}
                disabled={disabled}
                className="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm hover:bg-red-50 transition-colors"
              >
                清除
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
