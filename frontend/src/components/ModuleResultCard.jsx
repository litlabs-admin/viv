import { useState } from "react";

export default function ModuleResultCard({
  title,
  icon,
  score,
  status,
  summary,
  children,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);

  let scoreColor = "text-gray-500";
  let scoreBg = "bg-gray-100";
  if (typeof score === "number") {
    if (score >= 0.85) {
      scoreColor = "text-green-700";
      scoreBg = "bg-green-100";
    } else if (score >= 0.65) {
      scoreColor = "text-yellow-700";
      scoreBg = "bg-yellow-100";
    } else {
      scoreColor = "text-red-700";
      scoreBg = "bg-red-100";
    }
  }

  const statusBadge = {
    success: "bg-green-100 text-green-700",
    skipped: "bg-gray-100 text-gray-600",
    error: "bg-red-100 text-red-700",
    parse_error: "bg-orange-100 text-orange-700",
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center gap-3 flex-1">
          <span className="text-2xl">{icon}</span>
          <div className="flex-1">
            <div className="font-semibold text-gray-800">{title}</div>
            {summary && (
              <div className="text-xs text-gray-500 mt-0.5">{summary}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {typeof score === "number" && (
            <span
              className={`px-2 py-1 rounded text-xs font-semibold ${scoreColor} ${scoreBg}`}
            >
              {(score * 100).toFixed(0)}%
            </span>
          )}
          {status && (
            <span
              className={`px-2 py-1 rounded text-xs font-medium ${
                statusBadge[status] || "bg-gray-100 text-gray-600"
              }`}
            >
              {status}
            </span>
          )}
          <span className="text-gray-400 text-sm">
            {open ? "\u25B2" : "\u25BC"}
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-gray-100 p-4 bg-gray-50">{children}</div>
      )}
    </div>
  );
}
