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
      return "bg-green-50 text-green-800";
    case "yellow":
      return "bg-amber-50 text-amber-800";
    case "red":
      return "bg-red-50 text-red-800";
    default:
      return "bg-gray-50 text-gray-600";
  }
}

/** Pill/tag style: slightly stronger background for small badges */
export function getRiskPillColor(risk: string): string {
  switch (risk) {
    case "green":
      return "bg-green-100 text-green-800";
    case "yellow":
      return "bg-amber-100 text-amber-800";
    case "red":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-600";
  }
}

/** Large badge style: soft bg + border, for the main risk indicator */
export function getRiskBadgeClass(risk: string): string {
  switch (risk) {
    case "green":
      return "bg-green-50 text-green-800 border-green-200 border";
    case "yellow":
      return "bg-amber-50 text-amber-800 border-amber-200 border";
    case "red":
      return "bg-red-50 text-red-800 border-red-200 border";
    default:
      return "bg-gray-50 text-gray-600 border-gray-200 border";
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
      return "risk-dot-green bg-green-500";
    case "yellow":
      return "risk-dot-yellow bg-amber-500";
    case "red":
      return "risk-dot-red bg-red-500";
    default:
      return "bg-gray-400";
  }
}
