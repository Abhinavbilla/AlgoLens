import type { ReactNode } from "react";

// The small subset of Markdown our descriptions use: `code`, *emphasis* and **strong**.
// Builds React elements directly (never HTML strings), so text can't inject markup.
export function InlineMarkdown({ text }: { text: string }) {
  return <>{render(text)}</>;
}

const TOKEN = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g;

function render(text: string): ReactNode[] {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return <code key={i}>{part.slice(1, -1)}</code>;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
}
