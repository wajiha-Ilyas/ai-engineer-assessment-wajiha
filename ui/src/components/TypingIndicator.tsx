export function TypingIndicator() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.4rem",
        marginBottom: "1rem",
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "#7c3aed",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "0.85rem",
          color: "#fff",
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        N
      </div>
      <div
        style={{
          background: "#f1f5f9",
          borderRadius: "1rem 1rem 1rem 0.25rem",
          padding: "0.65rem 1rem",
          display: "flex",
          gap: "0.3rem",
          alignItems: "center",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "#94a3b8",
              display: "inline-block",
              animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
        <style>{`
          @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-6px); }
          }
        `}</style>
      </div>
    </div>
  );
}
