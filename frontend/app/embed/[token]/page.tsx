import EmbedClient from "./EmbedClient";

export default async function EmbedPage({
  params,
  searchParams,
}: {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { token } = await params;
  const { lang } = await searchParams;
  return <EmbedClient token={token} lang={lang || "ja"} />;
}
