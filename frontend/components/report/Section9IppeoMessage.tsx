interface Section9IppeoMessageProps {
  paragraphs: string[];
  final_summary: string;
}

export default function Section9IppeoMessage({ paragraphs, final_summary }: Section9IppeoMessageProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        イッポからの一言
      </h3>
      <div className="bg-coral/5 border border-coral/20 rounded-xl p-5 space-y-4">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-sm text-text-dark leading-relaxed">{p}</p>
        ))}
      </div>

      {/* 최종 정리 */}
      <div className="mt-6 bg-white rounded-xl p-5 card-shadow border-l-4 border-coral">
        <p className="text-xs font-bold text-coral mb-2">&#x1F4CC; 最終整理</p>
        <p className="text-sm font-medium text-text-dark leading-relaxed">{final_summary}</p>
      </div>
    </section>
  );
}
