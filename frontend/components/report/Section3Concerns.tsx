interface ConcernPoint {
  title: string;
  sub: string;
}

interface Section3Props {
  points: ConcernPoint[];
  supplement: string;
}

export default function Section3Concerns({ points, supplement }: Section3Props) {
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
            <span className="material-symbols-outlined text-amber-500">
              warning
            </span>
            <div>
              <p className="text-sm font-bold">{point.title}</p>
              <p className="text-xs text-gray-500 mt-1">{point.sub}</p>
            </div>
          </div>
        ))}
        <p className="text-[11px] text-gray-400 text-center italic">
          {supplement}
        </p>
      </div>
    </section>
  );
}
