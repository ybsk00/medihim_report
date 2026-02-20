interface Section2CauseAnalysisProps {
  intro: string;
  causes: string[];
  conclusion: string;
}

export default function Section2CauseAnalysis({ intro, causes, conclusion }: Section2CauseAnalysisProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        現在の状態と原因
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow">
        <p className="text-sm text-text-dark leading-relaxed mb-4">{intro}</p>
        <ul className="space-y-2 mb-4">
          {causes.map((cause, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-gray-400 mt-1 text-xs">&#x2022;</span>
              <span className="text-sm text-gray-700 leading-relaxed">{cause}</span>
            </li>
          ))}
        </ul>
        <p className="text-sm font-medium text-text-dark leading-relaxed">{conclusion}</p>
      </div>
    </section>
  );
}
