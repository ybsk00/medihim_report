interface ReportHeaderProps {
  title: string;
  date: string;
}

export default function ReportHeader({ title, date }: ReportHeaderProps) {
  return (
    <header className="glass-header sticky top-0 z-40 border-b border-gray-100 px-5 py-5">
      <div className="flex items-center justify-center gap-2 mb-4">
        <img
          src="/ippeo-logo.png"
          alt="IPPEO"
          className="w-5 h-5 rounded"
        />
        <h1 className="text-xs font-bold text-gray-500 tracking-tight">
          IPPEO | オンライン相談リポート
        </h1>
      </div>
      <div className="text-center">
        <h2 className="text-xl font-black text-text-dark leading-tight">
          {title}
        </h2>
        <p className="text-[11px] text-gray-400 mt-2 font-medium">
          {date.startsWith("作成日") ? date : `作成日：${date}`}
        </p>
      </div>
    </header>
  );
}
