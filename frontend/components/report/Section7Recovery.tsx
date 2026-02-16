interface RecoveryInfo {
  period: string;
  detail: string;
}

interface Section7Props {
  info: RecoveryInfo[];
  closing: string;
  gentle_note?: string;
}

export default function Section7Recovery({ info, closing, gentle_note }: Section7Props) {
  return (
    <section>
      <h3 className="text-lg font-bold text-text-dark mb-4 flex items-center gap-2">
        <span className="w-1 h-6 bg-coral rounded-full"></span>
        回復とスケジュールについて
      </h3>
      <div className="bg-white rounded-lg card-shadow overflow-hidden mb-4">
        <table className="w-full text-xs text-left">
          <thead className="bg-gray-50 text-gray-500 font-bold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">期間</th>
              <th className="px-4 py-3">状態・ケア</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {info.map((item, i) => (
              <tr key={i}>
                <td className="px-4 py-3 font-bold text-text-dark whitespace-nowrap">
                  {item.period}
                </td>
                <td className="px-4 py-3 leading-relaxed">{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="bg-coral/5 p-5 rounded-lg border border-coral/20 text-center">
        <p className="text-sm font-bold text-coral mb-2">次の一歩に向けて</p>
        <p className="text-sm text-text-dark leading-[1.8]">{closing}</p>
      </div>
      {gentle_note && (
        <p className="text-sm text-gray-500 text-center mt-3 leading-relaxed">
          {gentle_note}
        </p>
      )}
    </section>
  );
}
