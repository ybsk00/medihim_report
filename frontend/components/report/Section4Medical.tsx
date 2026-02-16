import type { ReportCitation } from "@/lib/api";

interface MedicalExplanation {
  number: number;
  title: string;
  text: string;
  citation?: ReportCitation;
  // V1 compat
  label?: string;
  icon?: string;
}

interface Section4Props {
  explanations: MedicalExplanation[];
  footnote?: string;
}

export default function Section4Medical({ explanations, footnote }: Section4Props) {
  // V1 감지: text 필드 없으면 구형 아이콘 카드 렌더링
  const isV1 = explanations.length > 0 && !explanations[0].text;

  if (isV1) {
    return (
      <section className="fade-in-section">
        <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-coral rounded-full"></span>
          そのように感じられた理由について
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {explanations.map((exp, i) => (
            <div key={i} className="bg-white p-4 rounded-lg card-shadow text-center">
              <span className="material-symbols-outlined text-soft-blue mb-2 text-3xl">
                {exp.icon}
              </span>
              <p className="text-[10px] font-bold text-coral mb-1">{exp.label}</p>
              <p className="text-xs font-bold leading-tight">{exp.title}</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        そのように感じられた理由について
      </h3>
      <div className="space-y-4">
        {explanations.map((exp, i) => (
          <div key={i} className="bg-white rounded-lg p-5 card-shadow">
            <div className="flex items-center gap-3 mb-3">
              <span className="flex-shrink-0 w-7 h-7 bg-coral/10 text-coral rounded-full flex items-center justify-center text-sm font-bold">
                {exp.number || i + 1}
              </span>
              <h4 className="text-sm font-bold text-text-dark">{exp.title}</h4>
            </div>
            <p className="text-sm text-text-dark leading-[1.8] mb-2">{exp.text}</p>
            {exp.citation && (
              <div className="mt-3 bg-slate-50 border-l-3 border-l-[3px] border-blue-400 rounded-r-lg p-3">
                <p className="text-[11px] text-gray-500 mb-1">
                  {exp.citation.stat && (
                    <span className="font-semibold text-blue-600">{exp.citation.stat} — </span>
                  )}
                  <a
                    href={exp.citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:underline"
                  >
                    {exp.citation.title}
                  </a>
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
      {footnote && (
        <p className="text-[11px] text-gray-400 mt-4 text-center leading-relaxed">
          {footnote}
        </p>
      )}
    </section>
  );
}
