import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

export default function FileUploader({ onFileSelected, selectedFile }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onFileSelected(acceptedFiles[0]);
      }
    },
    [onFileSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
        isDragActive
          ? "border-blue-500 bg-blue-50"
          : selectedFile
          ? "border-green-400 bg-green-50"
          : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
      }`}
    >
      <input {...getInputProps()} />

      {selectedFile ? (
        <div>
          <div className="text-4xl mb-3">&#128196;</div>
          <p className="text-lg font-medium text-gray-800">
            {selectedFile.name}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {(selectedFile.size / 1024).toFixed(1)} KB
          </p>
          <p className="text-sm text-blue-500 mt-2">
            Click or drag to replace
          </p>
        </div>
      ) : (
        <div>
          <div className="text-4xl mb-3">&#128228;</div>
          {isDragActive ? (
            <p className="text-lg text-blue-600">Drop the document here...</p>
          ) : (
            <>
              <p className="text-lg text-gray-600">
                Drag & drop a document image here
              </p>
              <p className="text-sm text-gray-400 mt-2">
                or click to browse (JPG, PNG, PDF - max 20MB)
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
