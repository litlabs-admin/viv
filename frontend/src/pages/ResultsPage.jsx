import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getResults } from "../api/client";
import VerdictBanner from "../components/VerdictBanner";
import ConfidenceGauge from "../components/ConfidenceGauge";
import ModuleResultCard from "../components/ModuleResultCard";
import ExtractedDataTable from "../components/ExtractedDataTable";

function formatDocType(type) {
  const map = {
    sppu_marksheet: "SPPU Marksheet",
    aadhaar_card: "Aadhaar Card",
    pan_card: "PAN Card",
    experience_certificate: "Experience Certificate",
    unknown: "Unknown",
  };
  return map[type] || type || "Unknown";
}

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

  const verification = data.verification;
  const report = verification?.full_report || {};
  const ocr = report.ocr || {};
  const ruleValidation = report.rule_validation || {};
  const nlp = report.nlp_consistency || {};
  const cnnForgery = report.cnn_forgery || {};
  const anomaly = report.anomaly_detection || {};
  const moduleScores = report.module_scores || {};
  const weights = report.weights || {};

  const annotatedImageUrl = verification?.annotated_image_path
    ? `/outputs/${documentId}_annotated.jpg`
    : null;

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <div className="mb-6">
        <Link
          to="/upload"
          className="text-sm text-blue-600 hover:underline"
        >
          &larr; Verify another document
        </Link>
      </div>

      <h1 className="text-3xl font-bold text-gray-800 mb-2">
        Verification Results
      </h1>
      <p className="text-gray-500 text-sm mb-6">
        Document ID: <span className="font-mono">{documentId}</span>
      </p>

      {verification ? (
        <>
          {/* Verdict Banner */}
          <div className="mb-6">
            <VerdictBanner
              verdict={verification.verdict}
              confidenceScore={verification.confidence_score}
            />
          </div>

          {/* Summary + Gauge */}
          <div className="grid md:grid-cols-3 gap-6 mb-6">
            <div className="md:col-span-2 bg-white border border-gray-200 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Summary
              </h2>
              <p className="text-gray-700 text-sm leading-relaxed">
                {report.summary || "No summary available."}
              </p>
              {report.override_reason && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
                  <strong>Override:</strong> {report.override_reason}
                </div>
              )}
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-gray-500">Document Type:</span>{" "}
                  <span className="font-medium text-gray-800">
                    {formatDocType(data.document_type)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Filename:</span>{" "}
                  <span className="font-medium text-gray-800 break-all">
                    {data.filename}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Processing Time:</span>{" "}
                  <span className="font-medium text-gray-800">
                    {verification.processing_time_ms
                      ? `${(verification.processing_time_ms / 1000).toFixed(1)}s`
                      : "-"}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Analyzed At:</span>{" "}
                  <span className="font-medium text-gray-800">
                    {verification.created_at
                      ? new Date(verification.created_at).toLocaleString()
                      : "-"}
                  </span>
                </div>
              </div>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-center">
              <ConfidenceGauge
                score={verification.confidence_score || 0}
                label="Final Score"
              />
            </div>
          </div>

          {/* Document Images */}
          {annotatedImageUrl && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Annotated Document
              </h2>
              <img
                src={annotatedImageUrl}
                alt="Annotated document"
                className="max-h-96 mx-auto rounded-lg border border-gray-200"
              />
            </div>
          )}

          {/* Score Breakdown */}
          {Object.keys(moduleScores).length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Score Breakdown
              </h2>
              <div className="space-y-2">
                {Object.entries(moduleScores).map(([key, score]) => {
                  const weight = weights[key] || 0;
                  const pct = Math.round((score || 0) * 100);
                  let barColor = "bg-green-500";
                  if (pct < 65) barColor = "bg-red-500";
                  else if (pct < 85) barColor = "bg-yellow-500";
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-gray-700 capitalize">
                          {key.replace(/_/g, " ")}{" "}
                          <span className="text-gray-400">
                            (weight: {(weight * 100).toFixed(0)}%)
                          </span>
                        </span>
                        <span className="font-semibold text-gray-800">
                          {pct}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`${barColor} h-2 rounded-full transition-all`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Module Cards */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-800 mt-8 mb-2">
              Module Results
            </h2>

            {/* OCR */}
            <ModuleResultCard
              title="OCR Extraction"
              icon="\u{1F4C4}"
              status={ocr.status}
              summary={
                ocr.extracted_fields
                  ? `${Object.keys(ocr.extracted_fields).length} fields extracted`
                  : "No data extracted"
              }
              defaultOpen={true}
            >
              <ExtractedDataTable data={ocr.extracted_fields} />
            </ModuleResultCard>

            {/* Rule Validation */}
            <ModuleResultCard
              title="Rule Validation"
              icon="\u2705"
              score={ruleValidation.score}
              status={ruleValidation.status}
              summary={`${ruleValidation.passed_count || 0} passed, ${
                ruleValidation.failed_count || 0
              } failed`}
            >
              <div className="space-y-4">
                {ruleValidation.passed && ruleValidation.passed.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-green-700 mb-2">
                      Passed ({ruleValidation.passed.length})
                    </h4>
                    <ul className="space-y-1">
                      {ruleValidation.passed.map((r, i) => (
                        <li
                          key={i}
                          className="text-xs text-gray-700 flex items-start gap-2"
                        >
                          <span className="text-green-600">&#10003;</span>
                          <span>
                            {typeof r === "object"
                              ? r.description || r.rule
                              : r}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {ruleValidation.failed && ruleValidation.failed.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-red-700 mb-2">
                      Failed ({ruleValidation.failed.length})
                    </h4>
                    <ul className="space-y-1">
                      {ruleValidation.failed.map((r, i) => (
                        <li
                          key={i}
                          className="text-xs text-gray-700 flex items-start gap-2"
                        >
                          <span className="text-red-600">&#10007;</span>
                          <span>
                            {typeof r === "object" ? (
                              <>
                                {r.description || r.rule}
                                {r.severity && (
                                  <span
                                    className={`ml-2 px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                      r.severity === "high"
                                        ? "bg-red-100 text-red-700"
                                        : "bg-yellow-100 text-yellow-700"
                                    }`}
                                  >
                                    {r.severity}
                                  </span>
                                )}
                              </>
                            ) : (
                              r
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(!ruleValidation.passed || ruleValidation.passed.length === 0) &&
                  (!ruleValidation.failed ||
                    ruleValidation.failed.length === 0) && (
                    <p className="text-sm text-gray-400 italic">
                      No rules evaluated
                    </p>
                  )}
              </div>
            </ModuleResultCard>

            {/* NLP Consistency */}
            <ModuleResultCard
              title="NLP Consistency"
              icon="\u{1F9E0}"
              score={nlp.score}
              status={nlp.status}
              summary={
                nlp.findings && nlp.findings.length > 0
                  ? `${nlp.findings.length} finding(s)`
                  : "No inconsistencies found"
              }
            >
              {nlp.findings && nlp.findings.length > 0 ? (
                <ul className="space-y-1">
                  {nlp.findings.map((f, i) => (
                    <li
                      key={i}
                      className="text-xs text-gray-700 flex items-start gap-2"
                    >
                      <span className="text-yellow-600">&#9888;</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500">
                  No semantic inconsistencies detected.
                </p>
              )}
            </ModuleResultCard>

            {/* CNN Forgery */}
            <ModuleResultCard
              title="CNN Forgery Detection"
              icon="\u{1F50D}"
              score={1 - (cnnForgery.forgery_probability || 0)}
              status={cnnForgery.status}
              summary={
                cnnForgery.forgery_detected
                  ? `Forgery detected (${((cnnForgery.forgery_probability || 0) * 100).toFixed(0)}% probability)`
                  : `No forgery detected (${((cnnForgery.forgery_probability || 0) * 100).toFixed(0)}% probability)`
              }
            >
              <div className="space-y-4">
                <div className="text-sm">
                  <div className="flex justify-between py-1">
                    <span className="text-gray-500">Method:</span>
                    <span className="font-medium">
                      {cnnForgery.method || "—"}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-gray-500">Forgery Probability:</span>
                    <span className="font-medium">
                      {((cnnForgery.forgery_probability || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-gray-500">Detected:</span>
                    <span className="font-medium">
                      {cnnForgery.forgery_detected ? "Yes" : "No"}
                    </span>
                  </div>
                </div>

                {(cnnForgery.ela_image_base64 ||
                  cnnForgery.gradcam_heatmap_base64) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {cnnForgery.ela_image_base64 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-2">
                          Error Level Analysis (ELA)
                        </p>
                        <img
                          src={`data:image/png;base64,${cnnForgery.ela_image_base64}`}
                          alt="ELA"
                          className="w-full rounded border border-gray-200"
                        />
                      </div>
                    )}
                    {cnnForgery.gradcam_heatmap_base64 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-2">
                          Grad-CAM Heatmap
                        </p>
                        <img
                          src={`data:image/png;base64,${cnnForgery.gradcam_heatmap_base64}`}
                          alt="Grad-CAM"
                          className="w-full rounded border border-gray-200"
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </ModuleResultCard>

            {/* Anomaly Detection */}
            <ModuleResultCard
              title="Anomaly Detection"
              icon="\u{1F4CA}"
              score={1 - (anomaly.anomaly_score || 0)}
              status={anomaly.status}
              summary={
                anomaly.is_anomaly
                  ? "Statistical anomaly detected"
                  : "Values within expected range"
              }
            >
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Method:</span>
                  <span className="font-medium">{anomaly.method || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Anomaly Score:</span>
                  <span className="font-medium">
                    {((anomaly.anomaly_score || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Is Anomaly:</span>
                  <span className="font-medium">
                    {anomaly.is_anomaly ? "Yes" : "No"}
                  </span>
                </div>
              </div>
            </ModuleResultCard>
          </div>

          {/* Actions */}
          <div className="flex gap-3 mt-8">
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
        </>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5">
          <p className="text-yellow-800">
            No verification data available yet for this document.
          </p>
        </div>
      )}
    </div>
  );
}
