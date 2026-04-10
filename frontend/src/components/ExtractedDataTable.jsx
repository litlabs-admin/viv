function formatValue(value) {
  if (value === null || value === undefined) return <span className="text-gray-400">—</span>;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-400">(empty)</span>;
    if (typeof value[0] === "object") {
      return (
        <div className="space-y-1">
          {value.map((item, idx) => (
            <div key={idx} className="text-xs bg-gray-100 rounded px-2 py-1">
              {Object.entries(item).map(([k, v]) => (
                <span key={k} className="mr-2">
                  <span className="text-gray-500">{k}:</span>{" "}
                  <span className="font-medium">{String(v)}</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      );
    }
    return value.join(", ");
  }
  if (typeof value === "object") {
    return (
      <pre className="text-xs bg-gray-100 rounded p-2 overflow-x-auto">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }
  return String(value);
}

function formatKey(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ExtractedDataTable({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <p className="text-sm text-gray-400 italic">No data extracted</p>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <tbody>
          {Object.entries(data).map(([key, value], idx) => (
            <tr
              key={key}
              className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
            >
              <td className="px-3 py-2 text-gray-600 font-medium w-1/3 align-top">
                {formatKey(key)}
              </td>
              <td className="px-3 py-2 text-gray-800 align-top">
                {formatValue(value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
