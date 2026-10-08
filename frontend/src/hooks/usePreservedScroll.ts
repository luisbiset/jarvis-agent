import { useCallback, useEffect, useRef } from 'react';

export function usePreservedScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const stickToBottom = useRef(true);
  const onScroll = useCallback(() => {
    const node = ref.current;
    if (node) stickToBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 48;
  }, []);
  useEffect(() => {
    const node = ref.current;
    if (node && stickToBottom.current) node.scrollTop = node.scrollHeight;
  });
  return { ref, onScroll };
}
