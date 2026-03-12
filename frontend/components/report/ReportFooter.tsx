export default function ReportFooter() {
  return (
    <footer className="bg-white border-t border-gray-100 px-5 py-8 text-center">
      <div className="flex justify-center items-center gap-2 mb-5">
        <img
          src="/ippeo-logo.png"
          alt="IPPEO"
          className="w-5 h-5 rounded"
        />
        <span className="text-xs font-bold text-gray-500">
          IPPEO | オンライン相談リポート
        </span>
      </div>
      <a
        href="#"
        className="inline-flex items-center justify-center bg-coral text-white font-bold px-8 py-3 rounded-full text-sm mb-6 w-full card-shadow hover:bg-coral/90 transition-colors"
      >
        カウンセラーに相談する
      </a>
      <div className="space-y-2">
        <p className="text-[10px] text-gray-400 leading-relaxed">
          本リポートはカウンセリング時の内容を元に作成されたものであり、確定的な診断や治療を保証するものではありません。
        </p>
        <p className="text-[10px] text-gray-400">
          &copy; 2026 IPPEO Beauty Consultation.
        </p>
      </div>
    </footer>
  );
}
