interface DirectionItem {
  text: string;
  detail?: string;
}

interface Section2Props {
  // V2
  items?: DirectionItem[];
  conclusion?: string;
  interpretation?: string;
  // V1 compat
  desired?: string[];
  quote?: string;
}

export default function Section2Direction({
  items,
  conclusion,
  interpretation,
  desired,
  quote,
}: Section2Props) {
  // V1: desired[] + quote
  if (!items && desired) {
    return (
      <section>
        <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-coral rounded-full"></span>
          OO様がご希望されている方向
        </h3>
        <div className="space-y-4">
          <div className="bg-white rounded-lg p-5 card-shadow">
            <ul className="space-y-3">
              {desired.map((item, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-coral text-[22px]">check_circle</span>
                  <span className="text-sm font-medium">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          {quote && (
            <div className="bg-coral/10 border-l-4 border-coral p-4 rounded-r-lg">
              <p className="text-sm italic text-text-dark leading-relaxed">{quote}</p>
            </div>
          )}
        </div>
      </section>
    );
  }

  // V2: items[] + conclusion + interpretation
  const directionItems = items || [];

  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        OO様がご希望されている方向
      </h3>
      <div className="space-y-4">
        <div className="bg-white rounded-lg p-5 card-shadow">
          <ul className="space-y-4">
            {directionItems.map((item, i) => (
              <li key={i}>
                <div className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-coral text-[22px] flex-shrink-0 mt-0.5">
                    check_circle
                  </span>
                  <div>
                    <span className="text-sm font-bold text-text-dark">{item.text}</span>
                    {item.detail && (
                      <p className="text-sm text-gray-600 mt-1 leading-relaxed">{item.detail}</p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {conclusion && (
          <div className="bg-coral/10 border-l-4 border-coral p-4 rounded-r-lg">
            <p className="text-sm text-text-dark leading-[1.8]">{conclusion}</p>
          </div>
        )}

        {interpretation && (
          <p className="text-sm text-gray-600 leading-relaxed px-1">
            {interpretation}
          </p>
        )}
      </div>
    </section>
  );
}
