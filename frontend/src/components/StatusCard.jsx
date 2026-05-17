export function StatusCard({ title, value, note }) {
  return (
    <div className="status-card">
      <div className="status-title">{title}</div>
      <div className="status-value">{value}</div>
      <div className="status-note">{note}</div>
    </div>
  );
}
