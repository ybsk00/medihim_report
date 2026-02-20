interface Section6PrecautionsProps {
  points: string[];
}

export default function Section6Precautions({ points }: Section6PrecautionsProps) {
  const filtered = points.filter((p) => p && p.trim());
  if (filtered.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        施術前の注意事項
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow">
        <ul className="space-y-2">
          {filtered.map((point, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-amber-500 mt-0.5 text-sm">&#x26A0;</span>
              <span className="text-sm text-gray-700 leading-relaxed">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
