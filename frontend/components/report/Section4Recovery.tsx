interface Section4RecoveryProps {
  timeline: { period: string; detail: string }[];
  note?: string | null;
}

export default function Section4Recovery({ timeline, note }: Section4RecoveryProps) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="block w-1 h-6 bg-coral rounded-full"></span>
        予想回復スケジュール
      </h3>
      <div className="bg-white rounded-xl card-shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50">
              <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider w-1/4">
                期間
              </th>
              <th className="text-left px-5 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">
                状態・ケア
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {timeline.map((item, i) => (
              <tr key={i}>
                <td className="px-5 py-3 text-xs font-bold text-text-dark whitespace-nowrap">
                  {item.period}
                </td>
                <td className="px-5 py-3 text-xs text-gray-600 leading-relaxed">
                  {item.detail}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && (
        <p className="text-xs text-gray-500 mt-3 px-1 leading-relaxed">{note}</p>
      )}
    </section>
  );
}
