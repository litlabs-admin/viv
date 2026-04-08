import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getResults } from "../api/client";
import VerdictBanner from "../components/VerdictBanner";

export default function ResultsPage() {
  const { documentId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchResults() {
      try {
        const result = await getResults(documentId);
        setData(result);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load results");
      } finally {
        setLoading(false);
      }
    }
    fetchResults();
  }, [documentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 text-lg">Loading results...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-10 px-4">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
        <Link
          to="/upload"
          className="mt-4 inline-block text-blue-600 hover:underline"
        >
          Upload another document
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        Verification Results
      </h1>

      {/* Document Info */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          Document Info
        </h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">Filename:</span>{" "}
            <span className="text-gray-800 font-medium">{data.filename}</span>
          </div>
          <div>
            <span className="text-gray-500">Type:</span>{" "}
            <span className="text-gray-800 font-medium">
              {data.document_type || "Not classified yet"}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Status:</span>{" "}
            <span
              className={`font-medium ${
                data.status === "completed" ? "text-green-600" : "text-yellow-600"
              }`}
            >
              {data.status}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Uploaded:</span>{" "}
            <span className="text-gray-800">
              {data.uploaded_at
                ? new Date(data.uploaded_at).toLocaleString()
                : "-"}
            </span>
          </div>
        </div>
      </div>

      {/* Verdict Banner (will show when verification modules are implemented) */}
      {data.verification?.verdict && (
        <div className="mb-6">
          <VerdictBanner
            verdict={data.verification.verdict}
            confidenceScore={data.verification.confidence_score}
          />
        </div>
      )}

      {/* Phase 1: Show preprocessing status */}
      {data.status === "completed" && !data.verification && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
          <h2 className="text-lg font-semibold text-blue-800 mb-2">
            Phase 1: Preprocessing Complete
          </h2>
          <p className="text-blue-700 text-sm">
            Document has been preprocessed successfully. Full verification
            pipeline (OCR, Rule Validation, CNN Forgery Detection, NLP, Anomaly
            Detection) will be available in upcoming phases.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-6">
        <Link
          to="/upload"
          className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors no-underline"
        >
          Verify Another Document
        </Link>
        <Link
          to="/history"
          className="px-5 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors no-underline"
        >
          View History
        </Link>
      </div>
    </div>
  );
}
