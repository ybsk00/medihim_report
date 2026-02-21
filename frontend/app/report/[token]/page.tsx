import { Metadata } from "next";
import ReportClient from "./ReportClient";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://ippeo-medhim.web.app";

function getApiBase(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl && apiUrl.startsWith("http")) return apiUrl;
  return `${SITE_URL}/api`;
}

const DEFAULT_TITLE = "美容相談リポート | IPPEO";
const DEFAULT_DESC =
  "韓国美容医療の専門カウンセリングレポートをお届けします。";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ token: string }>;
}): Promise<Metadata> {
  const { token } = await params;

  const fallback: Metadata = {
    title: DEFAULT_TITLE,
    description: DEFAULT_DESC,
    openGraph: {
      title: DEFAULT_TITLE,
      description: DEFAULT_DESC,
      siteName: "IPPEO",
      locale: "ja_JP",
      type: "article",
      images: [{ url: `${SITE_URL}/ippeo-logo.png`, width: 480, height: 480 }],
    },
  };

  try {
    const res = await fetch(`${getApiBase()}/public/report/${token}`, {
      next: { revalidate: 300 },
    });

    if (!res.ok) return fallback;

    const data = await res.json();
    const reportData = data.report_data;
    const customerName = data.customer_name;

    const title = reportData?.title || `${customerName}様 美容相談リポート`;
    const ogTitle = `${title} | IPPEO`;

    // section1_key_summary の要点から説明文を生成
    let description = DEFAULT_DESC;
    if (reportData?.section1_key_summary?.points?.length) {
      const points: string[] = reportData.section1_key_summary.points.slice(
        0,
        2
      );
      description = points.join(" ｜ ");
      if (description.length > 100) {
        description = description.substring(0, 97) + "...";
      }
    }

    return {
      title: ogTitle,
      description,
      openGraph: {
        title: ogTitle,
        description,
        siteName: "IPPEO",
        locale: "ja_JP",
        type: "article",
        url: `${SITE_URL}/report/${token}`,
        images: [
          { url: `${SITE_URL}/ippeo-logo.png`, width: 480, height: 480 },
        ],
      },
    };
  } catch {
    return fallback;
  }
}

export default async function ConsumerReportPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <ReportClient token={token} />;
}
