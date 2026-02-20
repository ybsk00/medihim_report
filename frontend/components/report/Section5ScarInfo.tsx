interface Section5ScarInfoProps {
  points: string[];
}

export default function Section5ScarInfo({ points }: Section5ScarInfoProps) {
  const filtered = points.filter((p) => p && p.trim());
  if (filtered.length === 0) return null;
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        傷跡について
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow">
        <ul className="space-y-2">
          {filtered.map((point, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
              <span className="text-sm text-gray-700 leading-relaxed">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
