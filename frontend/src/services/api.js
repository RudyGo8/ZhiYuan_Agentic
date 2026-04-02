export function createApiService(baseUrl) {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, '');

  async function request(path, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body,
      signal,
      token
    } = options;

    const finalHeaders = { ...headers };
    if (token) {
      finalHeaders.Authorization = `Bearer ${token}`;
    }

    const finalOptions = {
      method,
      headers: finalHeaders,
      signal
    };

    if (body !== undefined) {
      if (body instanceof FormData) {
        finalOptions.body = body;
      } else {
        if (!finalHeaders['Content-Type']) {
          finalHeaders['Content-Type'] = 'application/json';
        }
        finalOptions.body = JSON.stringify(body);
      }
    }

    return fetch(`${normalizedBaseUrl}${path}`, finalOptions);
  }

  async function requestJson(path, options = {}) {
    const response = await request(path, options);
    const data = await response.json().catch(() => ({}));
    return { response, data };
  }

  return {
    request,
    requestJson
  };
}
