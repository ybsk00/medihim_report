interface RecoveryInfo {
  period: string;
  detail: string;
}

interface Section7Props {
  info: RecoveryInfo[];
  closing: string;
}

export default function Section7Recovery({ info, closing }: Section7Props) {
  return (
    <section className="fade-in-section">
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
                <td className="px-4 py-3 font-bold text-text-dark">
                  {item.period}
                </td>
                <td className="px-4 py-3">{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="bg-coral/5 p-5 rounded-lg border border-coral/20 text-center">
        <p className="text-sm font-bold text-coral mb-2">次の一歩に向けて</p>
        <p className="text-xs text-text-dark leading-relaxed">{closing}</p>
      </div>
    </section>
  );
}
