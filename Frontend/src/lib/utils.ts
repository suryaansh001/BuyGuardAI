import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatAuditEventTitle(event?: string | null) {
  if (!event) return "Unknown event";

  return event.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
