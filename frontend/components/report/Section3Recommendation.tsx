interface Section3RecommendationProps {
  primary: { label: string; items: string[] };
  secondary: { label: string; items: string[] };
  goal: string;
}

export default function Section3Recommendation({ primary, secondary, goal }: Section3RecommendationProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        ご提案 (Recommended Plan)
      </h3>
      <div className="space-y-4">
        {/* 1차 권장 */}
        <div className="bg-white rounded-xl p-5 card-shadow border-l-4 border-coral">
          <p className="text-xs font-bold text-coral mb-3">&#x25C6; {primary.label}</p>
          <ul className="space-y-2">
            {primary.items.map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                <span className="text-sm text-text-dark leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* 필요 시 병행 */}
        {secondary.items.length > 0 && (
          <div className="bg-white rounded-xl p-5 card-shadow border-l-4 border-gray-300">
            <p className="text-xs font-bold text-gray-500 mb-3">&#x25C6; {secondary.label}</p>
            <ul className="space-y-2">
              {secondary.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
                  <span className="text-sm text-gray-700 leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 목표 */}
        <p className="text-sm text-text-dark text-center font-medium px-2">{goal}</p>
      </div>
    </section>
  );
}
