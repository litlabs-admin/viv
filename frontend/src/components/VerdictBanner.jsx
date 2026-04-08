const verdictConfig = {
  VERIFIED: {
    bg: "bg-green-100",
    border: "border-green-400",
    text: "text-green-800",
    label: "VERIFIED - Authentic",
    icon: "\u2705",
  },
  NEEDS_REVIEW: {
    bg: "bg-yellow-100",
    border: "border-yellow-400",
    text: "text-yellow-800",
    label: "NEEDS REVIEW - Suspicious",
    icon: "\u26A0\uFE0F",
  },
  FRAUDULENT: {
    bg: "bg-red-100",
    border: "border-red-400",
    text: "text-red-800",
    label: "FRAUDULENT - Tampering Detected",
    icon: "\u274C",
  },
};

export default function VerdictBanner({ verdict, confidenceScore }) {
  const config = verdictConfig[verdict] || verdictConfig.NEEDS_REVIEW;

  return (
    <div
      className={`${config.bg} ${config.border} border-2 rounded-xl p-6 text-center`}
    >
      <div className="text-3xl mb-2">{config.icon}</div>
      <h2 className={`text-2xl font-bold ${config.text}`}>{config.label}</h2>
      {confidenceScore !== null && confidenceScore !== undefined && (
        <p className={`text-lg mt-2 ${config.text}`}>
          Confidence Score: {(confidenceScore * 100).toFixed(1)}%
        </p>
      )}
    </div>
  );
}
