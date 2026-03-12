import EmbedClient from "../../../[token]/EmbedClient";

export default async function PatientEmbedPage({
  params,
}: {
  params: Promise<{ lang: string; token: string }>;
}) {
  const { lang, token } = await params;
  return <EmbedClient token={token} lang={lang === "ko" ? "ko" : "ja"} />;
}
