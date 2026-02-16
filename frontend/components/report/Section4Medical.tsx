interface MedicalExplanation {
  label: string;
  icon: string;
  title: string;
}

interface Section4Props {
  explanations: MedicalExplanation[];
}

export default function Section4Medical({ explanations }: Section4Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        そのように感じられた理由について
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {explanations.map((exp, i) => (
          <div
            key={i}
            className="bg-white p-4 rounded-lg card-shadow text-center"
          >
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
