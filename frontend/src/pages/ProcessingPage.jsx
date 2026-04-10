import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { verifyDocument } from "../api/client";

const STEPS = [
  { key: "preprocessing", label: "Image Preprocessing", description: "Deskew, enhance, binarize" },
  { key: "classification", label: "Document Classification", description: "Identifying document type" },
  { key: "ocr", label: "OCR Extraction", description: "Reading text with vision AI" },
  { key: "rule", label: "Rule Validation", description: "Checking domain rules" },
  { key: "nlp", label: "NLP Consistency", description: "Semantic analysis" },
  { key: "forgery", label: "CNN Forgery Detection", description: "ELA + EfficientNet + Grad-CAM" },
  { key: "anomaly", label: "Anomaly Detection", description: "Isolation Forest analysis" },
  { key: "report", label: "Generating Report", description: "Aggregating final verdict" },
];

export default function ProcessingPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    // Animate through steps while verify runs in background
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 1500);

    async function runVerification() {
      try {
        await verifyDocument(documentId);
        clearInterval(stepInterval);
        setCurrentStep(STEPS.length);
        setTimeout(() => navigate(`/results/${documentId}`), 500);
      } catch (err) {
        clearInterval(stepInterval);
        setError(
          err.response?.data?.detail || err.message || "Verification failed"
        );
      }
    }

    runVerification();

    return () => clearInterval(stepInterval);
  }, [documentId, navigate]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4">
        <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 text-center">
          <div className="text-4xl mb-3">&#9888;</div>
          <h2 className="text-xl font-bold text-red-800 mb-2">
            Verification Failed
          </h2>
          <p className="text-red-700 text-sm mb-4">{error}</p>
          <button
            onClick={() => navigate("/upload")}
            className="px-5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-16 px-4">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Analyzing Document
        </h1>
        <p className="text-gray-500">
          Running 9-stage verification pipeline...
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentStep;
          const isActive = idx === currentStep;
          const isPending = idx > currentStep;

          return (
            <div
              key={step.key}
              className={`flex items-start gap-4 py-3 ${
                idx !== STEPS.length - 1 ? "border-b border-gray-100" : ""
              }`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  isDone
                    ? "bg-green-500 text-white"
                    : isActive
                    ? "bg-blue-500 text-white animate-pulse"
                    : "bg-gray-200 text-gray-400"
                }`}
              >
                {isDone ? "\u2713" : idx + 1}
              </div>
              <div className="flex-1">
                <div
                  className={`font-medium ${
                    isDone
                      ? "text-gray-500 line-through"
                      : isActive
                      ? "text-blue-700"
                      : "text-gray-400"
                  }`}
                >
                  {step.label}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {step.description}
                </div>
              </div>
              {isActive && (
                <div className="flex-shrink-0">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
              {isPending && (
                <div className="flex-shrink-0 text-gray-300 text-xs mt-2">
                  pending
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, (currentStep / STEPS.length) * 100)}%`,
            }}
          ></div>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">
          This may take 10-30 seconds depending on document complexity
        </p>
      </div>
    </div>
  );
}
