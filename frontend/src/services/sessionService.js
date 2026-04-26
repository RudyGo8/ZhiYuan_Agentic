export async function listSessions(api, token) {
  const { response, data } = await api.requestJson('/chat/sessions', { token });
  if (!response.ok) {
    const error = new Error(data.detail || 'Failed to load sessions');
    error.status = response.status;
    throw error;
  }
  return data.sessions || [];
}

export async function getSessionMessages(api, token, sessionId) {
  const { response, data } = await api.requestJson(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
    token
  });
  if (!response.ok) {
    const error = new Error(data.detail || 'Failed to load session messages');
    error.status = response.status;
    throw error;
  }
  return data.messages || [];
}

export async function removeSession(api, token, sessionId) {
  const { response, data } = await api.requestJson(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
    token
  });
  if (!response.ok) {
    const error = new Error(data.detail || 'Delete failed');
    error.status = response.status;
    throw error;
  }
  return data;
}
