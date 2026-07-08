import TitleCard from "./TitleCard";

function renderBlock(block, handlers) {
  if (block.type === "text") {
    return <p className="message-text">{block.content}</p>;
  }
  if (block.type === "title_cards") {
    return (
      <div className="inline-cards">
        {block.items.map((item) => (
          <TitleCard key={`${item.media_type}-${item.tmdb_id || item.tvdb_id || item.title}`} item={item} compact onAdd={handlers.onAdd} onDismiss={handlers.onDismiss} />
        ))}
      </div>
    );
  }
  if (block.type === "action_prompt" && block.action === "open_viewport") {
    return (
      <button type="button" className="viewport-link" onClick={() => handlers.onOpenViewport(block.payload)}>
        Expand {block.payload?.items?.length || 0} titles in turnstyle view
      </button>
    );
  }
  return null;
}

export default function ChatThread({ messages, onAdd, onDismiss, onOpenViewport }) {
  return (
    <div className="chat-thread">
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.role}`}>
          <div className="message-inner">
            {message.blocks.map((block, index) => (
              <div key={index}>{renderBlock(block, { onAdd, onDismiss, onOpenViewport })}</div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
