import type { RouteLabel } from "../types";

const ROUTE_COLORS: Record<RouteLabel, string> = {
  superhero: "#7c3aed",
  dataset: "#0369a1",
  both: "#065f46",
  none: "#6b7280",
};

const ROUTE_LABELS: Record<RouteLabel, string> = {
  superhero: "Superhero",
  dataset: "Dataset",
  both: "Superhero + Dataset",
  none: "General",
};

interface SourceListProps {
  route: RouteLabel;
}

export function SourceList({ route }: SourceListProps) {
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
        }}
      >
        {ROUTE_LABELS[route]}
      </span>
    </div>
  );
}
