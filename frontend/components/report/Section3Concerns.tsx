interface ConcernPoint {
  title: string;
  description?: string;
  // V1 compat
  sub?: string;
}

interface Section3Props {
  points: ConcernPoint[];
  interpretation?: string;
  // V1 compat
  supplement?: string;
}

export default function Section3Concerns({ points, interpretation, supplement }: Section3Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        OO様が特に気にされていたポイント
      </h3>
      <div className="bg-white rounded-lg p-5 card-shadow space-y-4">
        {points.map((point, i) => (
          <div
            key={i}
            className="flex items-start gap-3 border-b border-gray-50 pb-3 last:border-0 last:pb-0"
          >
            <span className="material-symbols-outlined text-amber-500 flex-shrink-0">
              warning
            </span>
            <div>
              <p className="text-sm font-bold">{point.title}</p>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                {point.description || point.sub}
              </p>
            </div>
          </div>
        ))}
      </div>
      {(interpretation || supplement) && (
        <p className="text-sm text-gray-600 mt-3 leading-relaxed px-1">
          {interpretation || supplement}
        </p>
      )}
    </section>
  );
}
