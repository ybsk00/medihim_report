export default function ReportFooter() {
  return (
    <footer className="bg-white border-t border-gray-100 p-8 text-center">
      <div className="flex justify-center items-center gap-2 mb-6">
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
        <span className="text-sm font-bold text-text-dark">
          イッポ | 化粧相談リポート
        </span>
      </div>
      <a
        href="#"
        className="inline-flex items-center justify-center bg-coral text-white font-bold px-8 py-3 rounded-full text-sm mb-8 w-full card-shadow hover:bg-coral/90 transition-colors"
      >
        カウンセラーに相談する
      </a>
      <div className="space-y-2">
        <p className="text-[10px] text-gray-400 leading-relaxed">
          本リポートはカウンセリング時の内容を元に作成されたものであり、確定的な診断や治療を保証するものではありません。
        </p>
        <p className="text-[10px] text-gray-400">
          &copy; 2026 IPPO Beauty Consultation.
        </p>
      </div>
    </footer>
  );
}
