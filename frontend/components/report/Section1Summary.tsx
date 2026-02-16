interface Section1Props {
  text: string;
  points: string[];
}

export default function Section1Summary({ text, points }: Section1Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        OO様のための今回のご相談まとめ
      </h3>
      <div className="bg-white rounded-lg p-5 card-shadow">
        <p className="text-sm text-text-dark leading-[1.8] mb-4">{text}</p>
        <ul className="space-y-3">
          {points.map((point, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="material-symbols-outlined text-soft-blue text-[20px]">
                diamond
              </span>
              <span className="text-sm text-text-dark">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
