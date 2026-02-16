interface ReportHeaderProps {
  title: string;
  date: string;
}

export default function ReportHeader({ title, date }: ReportHeaderProps) {
  return (
    <header className="glass-header sticky top-0 z-40 border-b border-gray-100 px-5 py-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="bg-coral p-1 rounded">
          <svg
            className="w-4 h-4 text-white"
            fill="none"
            viewBox="0 0 48 48"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M6 6H42L36 24L42 42H6L12 24L6 6Z"
              fill="currentColor"
            />
          </svg>
        </div>
        <h1 className="text-sm font-bold text-text-dark tracking-tight">
          イッポ | 化粧相談リポート
        </h1>
      </div>
      <div>
        <h2 className="text-2xl font-black text-text-dark leading-tight">
          {title}
        </h2>
        <p className="text-xs text-gray-500 mt-2 font-medium">
          作成日：{date}
        </p>
      </div>
    </header>
  );
}
