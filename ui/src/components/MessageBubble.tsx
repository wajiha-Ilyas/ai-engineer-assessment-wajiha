import type { ChatMessage } from "../types";
import { SourceList } from "./SourceList";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        marginBottom: "1rem",
      }}
    >
      {/* Avatar + name row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.4rem",
          marginBottom: "0.25rem",
          flexDirection: isUser ? "row-reverse" : "row",
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: isUser ? "#3b82f6" : "#7c3aed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "0.85rem",
            color: "#fff",
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {isUser ? "U" : "N"}
        </div>
        <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: 500 }}>
          {isUser ? "You" : "Nova"}
        </span>
      </div>

      {/* Bubble */}
      <div
        style={{
          maxWidth: "75%",
          background: isUser ? "#3b82f6" : message.error ? "#fee2e2" : "#f1f5f9",
          color: isUser ? "#fff" : message.error ? "#991b1b" : "#1e293b",
          borderRadius: isUser ? "1rem 1rem 0.25rem 1rem" : "1rem 1rem 1rem 0.25rem",
          padding: "0.65rem 0.9rem",
          lineHeight: 1.6,
          fontSize: "0.9rem",
          boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message.content}

        {/* Sources + route badge (Nova only) */}
        {!isUser && !message.error && message.route && (
          <SourceList sources={message.sources ?? []} route={message.route} />
        )}
      </div>
    </div>
  );
}
