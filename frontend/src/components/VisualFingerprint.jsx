import TitleCard from "./TitleCard";

function clusterKey(item) {
  if (item.genres?.length) return item.genres[0];
  if (item.recommendation_reason) {
    const words = item.recommendation_reason.split(/\s+/).slice(0, 2).join(" ");
    if (words) return words;
  }
  return "Discovery";
}

export function extractLatestCards(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (message.role !== "assistant") continue;
    const cards = message.blocks
      .filter((block) => block.type === "title_cards")
      .flatMap((block) => block.items || [])
      .filter((item) => item?.title || item?.tmdb_id || item?.tvdb_id || item?.rating_key);
    if (cards.length) return cards;
  }
  return [];
}

export function clusterCards(items) {
  const groups = new Map();
  for (const item of items) {
    const key = clusterKey(item);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  return [...groups.entries()].map(([tag, clusterItems]) => ({ tag, items: clusterItems }));
}

export default function VisualFingerprint({ messages, onAdd, onDismiss }) {
  const cards = extractLatestCards(messages);
  const clusters = clusterCards(cards);

  if (!clusters.length) {
    return (
      <div className="fingerprint-empty">
        <p className="eyebrow">Visual fingerprint</p>
        <p>Ask the curator for recommendations — title clusters will appear here grouped by genre and theme.</p>
      </div>
    );
  }

  return (
    <div className="fingerprint-panel">
      <header className="fingerprint-header">
        <p className="eyebrow">Visual fingerprint</p>
        <h2>{cards.length} titles · {clusters.length} clusters</h2>
      </header>
      <div className="fingerprint-clusters">
        {clusters.map(({ tag, items }) => (
          <section key={tag} className="fingerprint-cluster">
            <h3>{tag}</h3>
            <div className="fingerprint-track">
              {items.map((item) => (
                <TitleCard
                  key={`${item.media_type}-${item.tmdb_id || item.tvdb_id || item.title}`}
                  item={item}
                  compact
                  onAdd={onAdd}
                  onDismiss={onDismiss}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
