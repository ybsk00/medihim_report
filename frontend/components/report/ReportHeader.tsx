interface ReportHeaderProps {
  title: string;
  date: string;
}

export default function ReportHeader({ title, date }: ReportHeaderProps) {
  return (
    <header className="glass-header sticky top-0 z-40 border-b border-gray-100 px-5 py-4">
      <div className="flex items-center gap-2 mb-3">
        <img
          src="/ippeo-logo.png"
          alt="IPPEO"
          className="w-6 h-6 rounded"
        />
        <h1 className="text-sm font-bold text-text-dark tracking-tight">
          IPPEO | 化粧相談リポート
        </h1>
      </div>
      <div>
        <h2 className="text-2xl font-black text-text-dark leading-tight">
          {title}
        </h2>
        <p className="text-xs text-gray-500 mt-2 font-medium">
          {date.startsWith("作成日") ? date : `作成日：${date}`}
        </p>
      </div>
    </header>
  );
}
