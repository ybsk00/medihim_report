interface OptionCategory {
  category_label?: string;
  items: string[];
  // V1 compat
  title?: string;
  desc?: string;
}

interface Section6Props {
  recommended: OptionCategory;
  optional: OptionCategory;
  unnecessary: OptionCategory;
  comment?: string;
}

function isV1(cat: OptionCategory): boolean {
  return typeof cat.title === "string" && !Array.isArray(cat.items);
}

function CategoryBlock({
  data,
  badgeText,
  badgeColor,
  borderColor,
  dimmed,
}: {
  data: OptionCategory;
  badgeText: string;
  badgeColor: string;
  borderColor: string;
  dimmed?: boolean;
}) {
  // V1: 단일 title/desc
  if (isV1(data)) {
    return (
      <div className={`bg-white p-4 rounded-lg card-shadow border ${borderColor} ${dimmed ? "opacity-60" : ""}`}>
        <span className={`inline-block text-[10px] font-bold px-2 py-1 rounded mb-2 ${badgeColor}`}>
          {badgeText}
        </span>
        <p className={`text-sm font-bold ${dimmed ? "text-gray-400" : "text-text-dark"}`}>{data.title}</p>
        <p className={`text-[11px] mt-1 ${dimmed ? "text-gray-400" : "text-gray-500"}`}>{data.desc}</p>
      </div>
    );
  }

  // V2: 카테고리 + 복수 항목
  const items = data.items || [];
  return (
    <div className={`bg-white p-4 rounded-lg card-shadow border ${borderColor} ${dimmed ? "opacity-60" : ""}`}>
      <span className={`inline-block text-[10px] font-bold px-2 py-1 rounded mb-2 ${badgeColor}`}>
        {badgeText}
      </span>
      {data.category_label && (
        <p className={`text-sm font-bold mb-2 ${dimmed ? "text-gray-400" : "text-text-dark"}`}>
          {data.category_label}
        </p>
      )}
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className={`text-xs mt-0.5 ${dimmed ? "text-gray-300" : "text-gray-400"}`}>•</span>
            <span className={`text-sm leading-relaxed ${dimmed ? "text-gray-400" : "text-text-dark"}`}>
              {item}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Section6Options({
  recommended,
  optional,
  unnecessary,
  comment,
}: Section6Props) {
  return (
    <section className="fade-in-section">
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        選択肢の整理
      </h3>
      <div className="space-y-3">
        <CategoryBlock
          data={recommended}
          badgeText="RECOMMENDED"
          badgeColor="bg-green-100 text-green-700"
          borderColor="border-green-100"
        />
        <CategoryBlock
          data={optional}
          badgeText="SUGGESTION"
          badgeColor="bg-blue-100 text-soft-blue"
          borderColor="border-blue-100"
        />
        <CategoryBlock
          data={unnecessary}
          badgeText="NOT NEEDED"
          badgeColor="bg-gray-100 text-gray-500"
          borderColor="border-gray-100"
          dimmed
        />
      </div>

      {comment && (
        <p className="text-sm text-gray-600 text-center mt-4 leading-relaxed px-2">
          {comment}
        </p>
      )}
    </section>
  );
}
