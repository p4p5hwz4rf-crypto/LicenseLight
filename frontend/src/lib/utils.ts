import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getRiskLabel(risk: string): string {
  switch (risk) {
    case "green":
      return "低风险";
    case "yellow":
      return "中风险";
    case "red":
      return "高风险";
    default:
      return "未知";
  }
}

export function getRiskColor(risk: string): string {
  switch (risk) {
    case "green":
      return "bg-risk-green text-white";
    case "yellow":
      return "bg-risk-yellow text-white";
    case "red":
      return "bg-risk-red text-white";
    default:
      return "bg-gray-400 text-white";
  }
}

export function getRiskBorderColor(risk: string): string {
  switch (risk) {
    case "green":
      return "border-l-risk-green";
    case "yellow":
      return "border-l-risk-yellow";
    case "red":
      return "border-l-risk-red";
    default:
      return "border-l-gray-300";
  }
}

export function getRiskDotClass(risk: string): string {
  switch (risk) {
    case "green":
      return "risk-dot-green bg-risk-green";
    case "yellow":
      return "risk-dot-yellow bg-risk-yellow";
    case "red":
      return "risk-dot-red bg-risk-red";
    default:
      return "bg-gray-400";
  }
}
