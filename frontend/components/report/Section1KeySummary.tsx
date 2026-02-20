interface Section1KeySummaryProps {
  points: string[];
}

export default function Section1KeySummary({ points }: Section1KeySummaryProps) {
  const filtered = points.filter((p) => p && p.trim());
  if (filtered.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        ご相談の要点
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow">
        <ul className="space-y-3">
          {filtered.map((point, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="text-soft-blue text-base mt-0.5">
                <img src="/heart-icon.png" alt="" className="w-4 h-4 inline-block" />
              </span>
              <span className="text-sm text-text-dark leading-relaxed">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
