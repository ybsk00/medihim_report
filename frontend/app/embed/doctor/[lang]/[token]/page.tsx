import EmbedClient from "../../../[token]/EmbedClient";

export default async function DoctorEmbedPage({
  params,
}: {
  params: Promise<{ lang: string; token: string }>;
}) {
  const { lang, token } = await params;
  return <EmbedClient token={token} lang={lang === "ja" ? "ja" : "ko"} />;
}
