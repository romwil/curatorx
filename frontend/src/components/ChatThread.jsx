import TitleCard from "./TitleCard";
import InlineAlert from "./InlineAlert";
import MessageText from "./MessageText";

function renderBlock(block, handlers, role) {
  if (block.type === "text") {
    return <MessageText content={block.content} markdown={role === "assistant"} />;
  }
  if (block.type === "error") {
    return <MessageText content={block.content} className="message-text message-error-text" />;
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

export default function ChatThread({
  messages,
  chatError,
  onAdd,
  onDismiss,
  onOpenViewport,
  variant = "immersive",
  showErrors = true,
}) {
  return (
    <div className={`chat-thread ${variant === "compact" ? "chat-thread-compact" : ""}`}>
      {showErrors && chatError ? <InlineAlert type="error" message={chatError} /> : null}
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.role}`} data-testid={`chat-message-${message.role}`}>
          <div className="message-inner">
            {message.blocks.map((block, index) => (
              <div key={index}>{renderBlock(block, { onAdd, onDismiss, onOpenViewport }, message.role)}</div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
