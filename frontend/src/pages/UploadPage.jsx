import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FileUploader from "../components/FileUploader";
import { uploadDocument, verifyDocument } from "../api/client";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  function handleFileSelected(file) {
    setSelectedFile(file);
    setError(null);

    // Generate preview for images
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
      // Step 1: Upload
      const uploadResult = await uploadDocument(selectedFile);
      const docId = uploadResult.document_id;

      // Step 2: Verify (preprocessing only in Phase 1)
      await verifyDocument(docId);

      // Step 3: Navigate to results
      navigate(`/results/${docId}`);
    } catch (err) {
      setError(
        err.response?.data?.detail || err.message || "Something went wrong"
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">
        Document Verification
      </h1>
      <p className="text-gray-500 mb-8">
        Upload a document to verify its authenticity using AI-powered analysis.
      </p>

      <FileUploader
        onFileSelected={handleFileSelected}
        selectedFile={selectedFile}
      />

      {/* Image Preview */}
      {preview && (
        <div className="mt-6">
          <p className="text-sm text-gray-500 mb-2">Preview:</p>
          <img
            src={preview}
            alt="Document preview"
            className="max-h-64 mx-auto rounded-lg border border-gray-200 shadow-sm"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Verify Button */}
      <button
        onClick={handleVerify}
        disabled={!selectedFile || uploading}
        className={`mt-6 w-full py-3 rounded-lg text-white font-medium text-lg transition-colors ${
          !selectedFile || uploading
            ? "bg-gray-300 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 cursor-pointer"
        }`}
      >
        {uploading ? "Processing..." : "Verify Document"}
      </button>
    </div>
  );
}
