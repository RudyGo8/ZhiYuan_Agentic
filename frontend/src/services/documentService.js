export async function listDocuments(api, token) {
  const { response, data } = await api.requestJson('/documents', { token });
  if (!response.ok) {
    const error = new Error(data.detail || 'Failed to load documents');
    error.status = response.status;
    throw error;
  }
  return data.documents || [];
}

export async function uploadDocumentFile(api, token, file) {
  const formData = new FormData();
  formData.append('file', file);

  const { response, data } = await api.requestJson('/documents/upload', {
    method: 'POST',
    token,
    body: formData
  });
  if (!response.ok) {
    const error = new Error(data.detail || 'Upload failed');
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function removeDocument(api, token, filename) {
  const { response, data } = await api.requestJson(`/documents/${encodeURIComponent(filename)}`, {
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
