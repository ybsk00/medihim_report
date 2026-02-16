interface OptionItem {
  title: string;
  desc: string;
}

interface Section6Props {
  recommended: OptionItem;
  optional: OptionItem;
  unnecessary: OptionItem;
  comment?: string;
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
        {/* Recommended */}
        <div className="bg-white p-4 rounded-lg card-shadow border border-green-100">
          <div className="flex justify-between items-center mb-2">
            <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-1 rounded">
              RECOMMENDED
            </span>
          </div>
          <p className="text-sm font-bold text-text-dark">{recommended.title}</p>
          <p className="text-[11px] text-gray-500 mt-1">{recommended.desc}</p>
        </div>

        {/* Suggestion */}
        <div className="bg-white p-4 rounded-lg card-shadow border border-blue-100">
          <div className="flex justify-between items-center mb-2">
            <span className="bg-blue-100 text-soft-blue text-[10px] font-bold px-2 py-1 rounded">
              SUGGESTION
            </span>
          </div>
          <p className="text-sm font-bold text-text-dark">{optional.title}</p>
          <p className="text-[11px] text-gray-500 mt-1">{optional.desc}</p>
        </div>

        {/* Not Needed */}
        <div className="bg-white p-4 rounded-lg card-shadow border border-gray-100 opacity-60">
          <div className="flex justify-between items-center mb-2">
            <span className="bg-gray-100 text-gray-500 text-[10px] font-bold px-2 py-1 rounded">
              NOT NEEDED
            </span>
          </div>
          <p className="text-sm font-bold text-gray-400">{unnecessary.title}</p>
          <p className="text-[11px] text-gray-400 mt-1">{unnecessary.desc}</p>
        </div>
      </div>

      {comment && (
        <p className="text-xs text-gray-500 text-center mt-3 italic">
          {comment}
        </p>
      )}
    </section>
  );
}
