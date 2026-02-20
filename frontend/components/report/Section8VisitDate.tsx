interface Section8VisitDateProps {
  date: string | null;
  note?: string | null;
}

export default function Section8VisitDate({ date, note }: Section8VisitDateProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        ご来院予定日
      </h3>
      <div className="bg-white rounded-xl p-5 card-shadow text-center">
        <p className="text-2xl font-black text-text-dark">{date}</p>
        {note && (
          <p className="text-xs text-gray-500 mt-2">{note}</p>
        )}
      </div>
    </section>
  );
}
