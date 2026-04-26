export async function consumeChatStream(response, handlers = {}) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let eventEndIndex = buffer.indexOf('\n\n');

    while (eventEndIndex !== -1) {
      const eventStr = buffer.slice(0, eventEndIndex);
      buffer = buffer.slice(eventEndIndex + 2);
      eventEndIndex = buffer.indexOf('\n\n');

      if (!eventStr.startsWith('data: ')) continue;

      const dataStr = eventStr.slice(6);
      if (dataStr === '[DONE]') {
        handlers.onDone?.();
        continue;
      }

      try {
        const data = JSON.parse(dataStr);
        if (data.type === 'content') {
          handlers.onContent?.(data.content || '');
        } else if (data.type === 'trace') {
          handlers.onTrace?.(data.rag_trace || null);
        } else if (data.type === 'rag_step') {
          handlers.onRagStep?.(data.step || null);
        } else if (data.type === 'error') {
          handlers.onError?.(data.error || data.content || 'Unknown error');
        }
      } catch (error) {
        handlers.onParseError?.(error, dataStr);
      }
    }

    handlers.onChunk?.();
  }
}
