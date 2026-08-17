import { ChatWindow } from "./components/ChatWindow";

export default function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #ede9fe 0%, #dbeafe 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
        fontFamily:
          "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 680,
          height: "85vh",
          minHeight: 500,
        }}
      >
        <ChatWindow />
      </div>
    </div>
  );
}
