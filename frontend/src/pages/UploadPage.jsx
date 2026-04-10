import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FileUploader from "../components/FileUploader";
import { uploadDocument } from "../api/client";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  function handleFileSelected(file) {
    setSelectedFile(file);
    setError(null);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(file);
    } else {
      setPreview(null);
    }
  }

  async function handleVerify() {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);

    try {
      const uploadResult = await uploadDocument(selectedFile);
      const docId = uploadResult.document_id;
      navigate(`/processing/${docId}`);
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || "Something went wrong"
      );
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-10 px-4">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-800 mb-3">
          Document Verification System
        </h1>
        <p className="text-gray-600 text-lg">
          Upload a document to verify its authenticity with AI-powered analysis
        </p>
      </div>

      {/* Supported document types */}
      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">
          Supported Document Types
        </h3>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="px-3 py-1 bg-white text-blue-700 rounded-full border border-blue-200">
            SPPU Marksheet
          </span>
          <span className="px-3 py-1 bg-white text-blue-700 rounded-full border border-blue-200">
            Aadhaar Card
          </span>
          <span className="px-3 py-1 bg-white text-blue-700 rounded-full border border-blue-200">
            PAN Card
          </span>
          <span className="px-3 py-1 bg-white text-blue-700 rounded-full border border-blue-200">
            Experience Certificate
          </span>
        </div>
      </div>

      <FileUploader
        onFileSelected={handleFileSelected}
        selectedFile={selectedFile}
      />

      {preview && (
        <div className="mt-6 bg-white border border-gray-200 rounded-xl p-4">
          <p className="text-sm font-medium text-gray-700 mb-3">Preview</p>
          <img
            src={preview}
            alt="Document preview"
            className="max-h-80 mx-auto rounded-lg shadow-sm"
          />
        </div>
      )}

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
          <span className="text-lg">&#9888;</span>
          <div>
            <p className="font-medium">Upload failed</p>
            <p className="mt-1">{error}</p>
          </div>
        </div>
      )}

      <button
        onClick={handleVerify}
        disabled={!selectedFile || uploading}
        className={`mt-6 w-full py-4 rounded-xl text-white font-semibold text-lg transition-all ${
          !selectedFile || uploading
            ? "bg-gray-300 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg"
        }`}
      >
        {uploading ? "Uploading..." : "Verify Document"}
      </button>

      <p className="text-center text-xs text-gray-400 mt-4">
        Your document is processed locally. Nothing is sent to external services.
      </p>
    </div>
  );
}
