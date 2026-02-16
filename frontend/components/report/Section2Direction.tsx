interface Section2Props {
  desired: string[];
  quote: string;
}

export default function Section2Direction({ desired, quote }: Section2Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        OO様がご希望されている方向
      </h3>
      <div className="space-y-4">
        <div className="bg-white rounded-lg p-5 card-shadow">
          <ul className="space-y-3">
            {desired.map((item, i) => (
              <li key={i} className="flex items-center gap-3">
                <span className="material-symbols-outlined text-coral text-[22px]">
                  check_circle
                </span>
                <span className="text-sm font-medium">{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-coral/10 border-l-4 border-coral p-4 rounded-r-lg">
          <p className="text-sm italic text-text-dark leading-relaxed">
            {quote}
          </p>
        </div>
      </div>
    </section>
  );
}
