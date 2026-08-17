import type { RouteLabel, Source } from "../types";

const ROUTE_COLORS: Record<RouteLabel, string> = {
  superhero: "#7c3aed",
  dataset: "#0369a1",
  both: "#065f46",
  none: "#6b7280",
};

const ROUTE_LABELS: Record<RouteLabel, string> = {
  superhero: "Superhero API",
  dataset: "Dataset",
  both: "Superhero + Dataset",
  none: "General",
};

interface SourceListProps {
  sources: Source[];
  route: RouteLabel;
}

export function SourceList({ sources, route }: SourceListProps) {
  return (
    <div style={{ marginTop: "0.5rem" }}>
      <span
        style={{
          display: "inline-block",
          fontSize: "0.7rem",
          fontWeight: 600,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: "#fff",
          background: ROUTE_COLORS[route],
          borderRadius: "9999px",
          padding: "1px 8px",
          marginBottom: "0.4rem",
        }}
      >
        {ROUTE_LABELS[route]}
      </span>

      {sources.length > 0 && (
        <ul
          style={{
            margin: "0.25rem 0 0 0",
            padding: "0 0 0 1rem",
            fontSize: "0.75rem",
            color: "#64748b",
          }}
        >
          {sources.map((s, i) => (
            <li key={i}>
              {s.kind === "superhero_api" ? (
                <>
                  <strong>{s.name}</strong> — Superhero API
                </>
              ) : (
                <>
                  <strong>{s.title}</strong> (dataset)
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
