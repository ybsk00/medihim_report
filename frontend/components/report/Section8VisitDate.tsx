interface Section8VisitDateProps {
  date: string | null;
  note?: string | null;
  lang?: string;
}

export default function Section8VisitDate({ date, note, lang = "ja" }: Section8VisitDateProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        {lang === "ko" ? "내원 예정일" : "ご来院予定日"}
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow text-center">
        <p className="text-2xl font-black text-text-dark">{date || (lang === "ko" ? "미정" : "未定")}</p>
        {note && (
          <p className="text-xs text-gray-500 mt-2">{note}</p>
        )}
      </div>
    </section>
  );
}
