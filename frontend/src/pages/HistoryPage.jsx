import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../api/client";

const verdictBadge = {
  VERIFIED: "bg-green-100 text-green-800",
  NEEDS_REVIEW: "bg-yellow-100 text-yellow-800",
  FRAUDULENT: "bg-red-100 text-red-800",
};

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const data = await getHistory();
        setHistory(data.documents || []);
      } catch (err) {
        console.error("Failed to load history:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 text-lg">Loading history...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">
          Verification History
        </h1>
        <Link
          to="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm no-underline"
        >
          New Verification
        </Link>
      </div>

      {history.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">&#128196;</div>
          <p>No documents verified yet.</p>
          <Link to="/upload" className="text-blue-500 hover:underline text-sm">
            Upload your first document
          </Link>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Filename
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Type
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Verdict
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {history.map((doc) => (
                <tr
                  key={doc.document_id}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-3 px-4">
                    <Link
                      to={`/results/${doc.document_id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {doc.filename}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-gray-600">
                    {doc.document_type || "-"}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        doc.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : doc.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {doc.status}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {doc.verdict ? (
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          verdictBadge[doc.verdict] || ""
                        }`}
                      >
                        {doc.verdict}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-500">
                    {doc.uploaded_at
                      ? new Date(doc.uploaded_at).toLocaleDateString()
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
