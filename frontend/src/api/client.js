const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  getHealth: () => request('/health'),
  getProducts: (brand) => request(`/products${brand ? `?brand=${encodeURIComponent(brand)}` : ''}`),
  getReviews: (params = {}) => {
    const query = new URLSearchParams();
    if (params.productId) query.append('product_id', params.productId);
    if (params.source) query.append('source', params.source);
    if (params.minRating !== undefined && params.minRating !== '') query.append('min_rating', params.minRating);
    if (params.maxRating !== undefined && params.maxRating !== '') query.append('max_rating', params.maxRating);
    if (params.q) query.append('q', params.q);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);

    const queryString = query.toString();
    return request(`/reviews${queryString ? `?${queryString}` : ''}`);
  },
  getJobs: (status) => request(`/jobs${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  getJob: (jobId) => request(`/jobs/${jobId}`),
  triggerScrape: (payload) => request('/jobs/scrape', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
};
