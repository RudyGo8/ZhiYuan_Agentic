export async function openChatStream(api, token, { message, sessionId, signal }) {
  return api.request('/chat/stream', {
    method: 'POST',
    token,
    signal,
    body: {
      message,
      session_id: sessionId
    }
  });
}
