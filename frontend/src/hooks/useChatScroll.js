import { useCallback, useEffect, useRef, useState } from "react";

const SCROLL_PADDING = 16;
const NEW_REPLY_THRESHOLD_PX = 120;

export default function useChatScroll({ messages, loading, sessionId }) {
  const scrollRef = useRef(null);
  const prevSessionRef = useRef(sessionId);
  const prevCountRef = useRef(0);
  const [showNewReplyChip, setShowNewReplyChip] = useState(false);

  const isScrolledUp = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return false;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    return distanceFromBottom > NEW_REPLY_THRESHOLD_PX;
  }, []);

  const scrollToBottom = useCallback((behavior = "auto") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    setShowNewReplyChip(false);
  }, []);

  const scrollToMessage = useCallback((messageId, block = "start", behavior = "smooth") => {
    const el = scrollRef.current;
    if (!el) return;
    const node = el.querySelector(`[data-message-id="${messageId}"]`);
    if (!node) {
      scrollToBottom(behavior);
      return;
    }

    const nodeTop = node.offsetTop;
    const nodeBottom = nodeTop + node.offsetHeight;

    if (block === "end") {
      el.scrollTo({ top: Math.max(0, nodeBottom - el.clientHeight + SCROLL_PADDING), behavior });
      return;
    }

    if (block === "anchor") {
      const userNodes = el.querySelectorAll('[data-message-role="user"]');
      const prevUser = userNodes.length ? userNodes[userNodes.length - 1] : null;
      if (prevUser) {
        const userBottom = prevUser.offsetTop + prevUser.offsetHeight;
        const minScroll = userBottom - el.clientHeight + SCROLL_PADDING;
        const targetScroll = Math.min(nodeTop - SCROLL_PADDING, Math.max(minScroll, 0));
        el.scrollTo({ top: Math.max(0, targetScroll), behavior });
        return;
      }
    }

    el.scrollTo({ top: Math.max(0, nodeTop - SCROLL_PADDING), behavior });
  }, [scrollToBottom]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return undefined;

    function handleScroll() {
      if (!isScrolledUp()) {
        setShowNewReplyChip(false);
      }
    }

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, [isScrolledUp]);

  useEffect(() => {
    if (prevSessionRef.current !== sessionId) {
      prevSessionRef.current = sessionId;
      prevCountRef.current = messages.length;
      setShowNewReplyChip(false);
      requestAnimationFrame(() => scrollToBottom("auto"));
    }
  }, [sessionId, messages.length, scrollToBottom]);

  useEffect(() => {
    const count = messages.length;
    if (count === 0) {
      prevCountRef.current = 0;
      setShowNewReplyChip(false);
      return;
    }

    const isNewMessage = count > prevCountRef.current;
    if (!isNewMessage && !loading) return;

    const last = messages[count - 1];
    const wasScrolledUp = isScrolledUp();
    prevCountRef.current = count;

    requestAnimationFrame(() => {
      if (loading) {
        if (wasScrolledUp) {
          setShowNewReplyChip(true);
        } else {
          scrollToBottom("smooth");
        }
        return;
      }
      if (isNewMessage && last.role === "user") {
        if (wasScrolledUp) {
          setShowNewReplyChip(true);
        } else {
          scrollToMessage(last.id, "end");
        }
        return;
      }
      if (isNewMessage && last.role === "assistant") {
        if (wasScrolledUp) {
          setShowNewReplyChip(true);
        } else {
          scrollToMessage(last.id, "anchor");
        }
      }
    });
  }, [messages, loading, scrollToMessage, scrollToBottom, isScrolledUp]);

  return { scrollRef, showNewReplyChip, scrollToBottom };
}
