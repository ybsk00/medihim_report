interface ProposalStep {
  step: string;
  title: string;
  desc: string;
}

interface Section5Props {
  steps: ProposalStep[];
}

export default function Section5Proposal({ steps }: Section5Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        ご相談で整理された方向性
      </h3>
      <div className="space-y-4">
        {steps.map((s, i) => (
          <div
            key={i}
            className="bg-white rounded-lg p-5 border-l-4 border-coral card-shadow"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-coral font-black text-xl italic">
                {s.step}
              </span>
              <span className="text-sm font-bold text-text-dark">{s.title}</span>
            </div>
            <p className="text-xs text-gray-600">{s.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
