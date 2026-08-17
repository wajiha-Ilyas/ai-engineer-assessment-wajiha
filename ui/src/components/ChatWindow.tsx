import { useState, useRef, useEffect, useCallback } from "react";
import { askNova } from "../api";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

const SESSION_KEY = "nova_session_id";
const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm Nova, your AI assistant. I can answer questions about superheroes " +
    "(powers, biography, appearance) or countries (USA, Japan, Germany, Brazil, Australia). " +
    "What would you like to know?",
  route: "none",
  sources: [],
};

function uid() {
  return Math.random().toString(36).slice(2);
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(
    () => sessionStorage.getItem(SESSION_KEY) ?? undefined
  );

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = useCallback(async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    const userMsg: ChatMessage = { id: uid(), role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await askNova({ question, session_id: sessionId });

      // Persist session_id for subsequent requests
      if (data.session_id) {
        sessionStorage.setItem(SESSION_KEY, data.session_id);
        setSessionId(data.session_id);
      }

      const novaMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: data.answer,
        route: data.route,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, novaMsg]);
    } catch (err) {
      const errMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content:
          err instanceof Error ? err.message : "Something went wrong. Please try again.",
        error: true,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const clearChat = () => {
    sessionStorage.removeItem(SESSION_KEY);
    setSessionId(undefined);
    setMessages([WELCOME]);
    setInput("");
    inputRef.current?.focus();
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#fff",
        borderRadius: "1rem",
        boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)",
          padding: "1rem 1.25rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.2rem",
            }}
          >
            🤖
          </div>
          <div>
            <div style={{ color: "#fff", fontWeight: 700, fontSize: "1rem" }}>
              Nova
            </div>
            <div style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.75rem" }}>
              Superheroes &amp; Countries
            </div>
          </div>
        </div>
        <button
          onClick={clearChat}
          title="New conversation"
          style={{
            background: "rgba(255,255,255,0.15)",
            border: "none",
            borderRadius: "0.5rem",
            color: "#fff",
            padding: "0.35rem 0.75rem",
            cursor: "pointer",
            fontSize: "0.8rem",
            fontWeight: 500,
          }}
        >
          New chat
        </button>
      </div>

      {/* Session badge */}
      {sessionId && (
        <div
          style={{
            background: "#f8fafc",
            borderBottom: "1px solid #e2e8f0",
            padding: "0.35rem 1.25rem",
            fontSize: "0.7rem",
            color: "#94a3b8",
            fontFamily: "monospace",
          }}
        >
          Session: {sessionId}
        </div>
      )}

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "1.25rem",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Suggestion chips */}
      {messages.length === 1 && (
        <div
          style={{
            padding: "0 1.25rem 0.75rem",
            display: "flex",
            flexWrap: "wrap",
            gap: "0.4rem",
          }}
        >
          {[
            "Who is Spider-Man?",
            "Iron Man's powerstats",
            "Tell me about Japan",
            "GDP of Germany",
            "Hi!",
          ].map((chip) => (
            <button
              key={chip}
              onClick={() => {
                setInput(chip);
                inputRef.current?.focus();
              }}
              style={{
                background: "#f1f5f9",
                border: "1px solid #e2e8f0",
                borderRadius: "9999px",
                padding: "0.3rem 0.75rem",
                fontSize: "0.78rem",
                color: "#475569",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div
        style={{
          padding: "0.75rem 1rem",
          borderTop: "1px solid #e2e8f0",
          display: "flex",
          gap: "0.5rem",
          alignItems: "flex-end",
          background: "#f8fafc",
        }}
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about a superhero or a country…"
          rows={1}
          style={{
            flex: 1,
            resize: "none",
            border: "1px solid #cbd5e1",
            borderRadius: "0.75rem",
            padding: "0.6rem 0.85rem",
            fontSize: "0.9rem",
            lineHeight: 1.5,
            outline: "none",
            fontFamily: "inherit",
            background: "#fff",
            maxHeight: 120,
            overflowY: "auto",
            transition: "border-color 0.15s",
          }}
          onFocus={(e) => (e.target.style.borderColor = "#7c3aed")}
          onBlur={(e) => (e.target.style.borderColor = "#cbd5e1")}
          disabled={loading}
        />
        <button
          onClick={() => void send()}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim() ? "#e2e8f0" : "#7c3aed",
            color: loading || !input.trim() ? "#94a3b8" : "#fff",
            border: "none",
            borderRadius: "0.75rem",
            width: 42,
            height: 42,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            flexShrink: 0,
            transition: "background 0.15s",
            fontSize: "1.1rem",
          }}
          title="Send (Enter)"
        >
          ➤
        </button>
      </div>
    </div>
  );
}
