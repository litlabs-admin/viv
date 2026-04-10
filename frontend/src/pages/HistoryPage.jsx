import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../api/client";

const verdictBadge = {
  VERIFIED: "bg-green-100 text-green-800",
  NEEDS_REVIEW: "bg-yellow-100 text-yellow-800",
  FRAUDULENT: "bg-red-100 text-red-800",
};

const DOC_TYPES = [
  { value: "", label: "All Types" },
  { value: "sppu_marksheet", label: "SPPU Marksheet" },
  { value: "aadhaar_card", label: "Aadhaar Card" },
  { value: "pan_card", label: "PAN Card" },
  { value: "experience_certificate", label: "Experience Certificate" },
];

const VERDICTS = [
  { value: "", label: "All Verdicts" },
  { value: "VERIFIED", label: "Verified" },
  { value: "NEEDS_REVIEW", label: "Needs Review" },
  { value: "FRAUDULENT", label: "Fraudulent" },
];

function formatDocType(type) {
  const map = {
    sppu_marksheet: "SPPU Marksheet",
    aadhaar_card: "Aadhaar Card",
    pan_card: "PAN Card",
    experience_certificate: "Experience Certificate",
  };
  return map[type] || type || "-";
}

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [docTypeFilter, setDocTypeFilter] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      try {
        const params = {};
        if (docTypeFilter) params.doc_type = docTypeFilter;
        const data = await getHistory(params);
        setHistory(data.documents || []);
      } catch (err) {
        console.error("Failed to load history:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [docTypeFilter]);

  const filtered = history.filter((doc) => {
    if (verdictFilter && doc.verdict !== verdictFilter) return false;
    if (
      searchTerm &&
      !doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const stats = {
    total: history.length,
    verified: history.filter((d) => d.verdict === "VERIFIED").length,
    review: history.filter((d) => d.verdict === "NEEDS_REVIEW").length,
    fraudulent: history.filter((d) => d.verdict === "FRAUDULENT").length,
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Verification History
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            All documents analyzed through the verification pipeline
          </p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm no-underline font-medium"
        >
          + New Verification
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-xs text-gray-500 uppercase">Total</div>
          <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <div className="text-xs text-green-700 uppercase">Verified</div>
          <div className="text-2xl font-bold text-green-800">
            {stats.verified}
          </div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="text-xs text-yellow-700 uppercase">Needs Review</div>
          <div className="text-2xl font-bold text-yellow-800">
            {stats.review}
          </div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="text-xs text-red-700 uppercase">Fraudulent</div>
          <div className="text-2xl font-bold text-red-800">
            {stats.fraudulent}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            placeholder="Search by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={docTypeFilter}
            onChange={(e) => setDocTypeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {DOC_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {VERDICTS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-gray-500">Loading history...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">&#128196;</div>
          <p className="mb-3">
            {history.length === 0
              ? "No documents verified yet."
              : "No documents match your filters."}
          </p>
          {history.length === 0 && (
            <Link
              to="/upload"
              className="text-blue-500 hover:underline text-sm"
            >
              Upload your first document
            </Link>
          )}
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
                  Verdict
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Confidence
                </th>
                <th className="text-left py-3 px-4 text-gray-600 font-medium">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => (
                <tr
                  key={doc.document_id}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-3 px-4">
                    <Link
                      to={`/results/${doc.document_id}`}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {doc.filename}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-gray-600">
                    {formatDocType(doc.document_type)}
                  </td>
                  <td className="py-3 px-4">
                    {doc.verdict ? (
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          verdictBadge[doc.verdict] || ""
                        }`}
                      >
                        {doc.verdict.replace("_", " ")}
                      </span>
                    ) : (
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
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-700">
                    {doc.confidence_score !== null &&
                    doc.confidence_score !== undefined
                      ? `${(doc.confidence_score * 100).toFixed(0)}%`
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-xs">
                    {doc.uploaded_at
                      ? new Date(doc.uploaded_at).toLocaleString()
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
