import { collectAddableFromMessage } from "../lib/addActions";
import ConfirmAllButton from "./ConfirmAllButton";
import TitleCard from "./TitleCard";
import InlineAlert from "./InlineAlert";
import MessageText from "./MessageText";

function isDisplayableCard(item) {
  return Boolean(item?.title || item?.tmdb_id || item?.tvdb_id || item?.rating_key);
}

function renderBulkConfirmActions(message, handlers, showTokenConfirm) {
  const { radarr, sonarr } = collectAddableFromMessage(message);
  const actions = [];

  if (showTokenConfirm && handlers.pendingTokenCount >= 2) {
    actions.push(
      <ConfirmAllButton
        key="tokens"
        count={handlers.pendingTokenCount}
        variant="tokens"
        onClick={() => handlers.onConfirmAllTokens?.()}
        disabled={handlers.actionsDisabled}
      />
    );
    return actions.length ? <div className="bulk-confirm-actions">{actions}</div> : null;
  }

  if (radarr.length >= 2) {
    actions.push(
      <ConfirmAllButton
        key="radarr"
        count={radarr.length}
        target="radarr"
        onClick={() => handlers.onConfirmAllItems?.(radarr, "radarr")}
        disabled={handlers.actionsDisabled}
      />
    );
  }
  if (sonarr.length >= 2) {
    actions.push(
      <ConfirmAllButton
        key="sonarr"
        count={sonarr.length}
        target="sonarr"
        onClick={() => handlers.onConfirmAllItems?.(sonarr, "sonarr")}
        disabled={handlers.actionsDisabled}
      />
    );
  }

  return actions.length ? <div className="bulk-confirm-actions">{actions}</div> : null;
}

function renderBlock(block, handlers, role, message, blockIndex, blocks) {
  if (block.type === "text") {
    return <MessageText content={block.content} markdown={role === "assistant"} />;
  }
  if (block.type === "error") {
    return <MessageText content={block.content} className="message-text message-error-text" />;
  }
  if (block.type === "title_cards") {
    const items = (block.items || []).filter(isDisplayableCard);
    if (!items.length) return null;
    const isLastTitleCards = !blocks.slice(blockIndex + 1).some((entry) => entry.type === "title_cards");
    return (
      <>
        <div className="inline-cards">
          {items.map((item) => (
            <TitleCard key={`${item.media_type}-${item.tmdb_id || item.tvdb_id || item.title}`} item={item} compact onAdd={handlers.onAdd} onDismiss={handlers.onDismiss} />
          ))}
        </div>
        {role === "assistant" && isLastTitleCards
          ? renderBulkConfirmActions(message, handlers, handlers.pendingTokenCount >= 2)
          : null}
      </>
    );
  }
  if (block.type === "action_prompt" && block.action === "open_viewport") {
    return (
      <button type="button" className="viewport-link" data-testid="expand-title-cards" onClick={() => handlers.onOpenViewport?.(block.payload)}>
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
  onConfirmAllItems,
  onConfirmAllTokens,
  pendingTokenCount = 0,
  actionsDisabled = false,
  variant = "immersive",
  showErrors = true,
}) {
  const lastAssistantId = [...messages].reverse().find((message) => message.role === "assistant")?.id;

  return (
    <div className={`chat-thread ${variant === "compact" ? "chat-thread-compact" : ""}`}>
      {showErrors && chatError ? <InlineAlert type="error" message={chatError} /> : null}
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.role}`} data-testid={`chat-message-${message.role}`}>
          <div className="message-inner">
            {message.blocks.map((block, index) => (
              <div key={index}>
                {renderBlock(
                  block,
                  {
                    onAdd,
                    onDismiss,
                    onOpenViewport,
                    onConfirmAllItems,
                    onConfirmAllTokens,
                    pendingTokenCount: message.id === lastAssistantId ? pendingTokenCount : 0,
                    actionsDisabled,
                  },
                  message.role,
                  message,
                  index,
                  message.blocks
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
