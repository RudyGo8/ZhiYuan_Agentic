export async function fetchCurrentUser(api, token) {
  const { response, data } = await api.requestJson('/auth/me', { token });
  if (!response.ok) {
    const error = new Error(data.detail || 'Authentication failed');
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function login(api, payload) {
  const { response, data } = await api.requestJson('/auth/login', {
    method: 'POST',
    body: payload
  });
  if (!response.ok) {
    const error = new Error(data.detail || 'Login failed');
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function register(api, payload) {
  const { response, data } = await api.requestJson('/auth/register', {
    method: 'POST',
    body: payload
  });
  if (!response.ok) {
    const error = new Error(data.detail || 'Register failed');
    error.status = response.status;
    throw error;
  }
  return data;
}
