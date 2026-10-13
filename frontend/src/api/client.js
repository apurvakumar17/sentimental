const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
    if (params.ingestionMethod) query.append('ingestion_method', params.ingestionMethod);
    if (params.minRating !== undefined && params.minRating !== '') query.append('min_rating', params.minRating);
    if (params.maxRating !== undefined && params.maxRating !== '') query.append('max_rating', params.maxRating);
    if (params.q) query.append('q', params.q);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);

    const queryString = query.toString();
    return request(`/reviews${queryString ? `?${queryString}` : ''}`);
  },
  getReview: (reviewId) => request(`/reviews/${reviewId}`),
  getJobs: (status) => request(`/jobs${status ? `?status=${encodeURIComponent(status)}` : ''}`),
  getJob: (jobId) => request(`/jobs/${jobId}`),
  triggerScrape: (payload) => request('/jobs/scrape', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getDatasetQuality: (params = {}, config = {}) => {
    const query = new URLSearchParams();
    if (params.productId) query.append('product_id', params.productId);
    if (params.source) query.append('source', params.source);
    const queryString = query.toString();
    return request(`/datasets/quality${queryString ? `?${queryString}` : ''}`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },
  previewDataset: (filters = {}, limit = 10, offset = 0) => {
    return request(`/datasets/preview?limit=${limit}&offset=${offset}`, {
      method: 'POST',
      body: JSON.stringify(filters),
    });
  },
  exportDataset: (exportRequest) => request('/datasets/export', {
    method: 'POST',
    body: JSON.stringify(exportRequest),
  }),
  getDatasetExports: () => request('/datasets/exports'),
  getDownloadUrl: (filename) => `${API_BASE}/datasets/download/${encodeURIComponent(filename)}`,
  // Kaggle Dataset Import
  previewImport: (formData) => request('/imports/preview', {
    method: 'POST',
    body: formData,
  }),
  startImport: (formData) => request('/imports', {
    method: 'POST',
    body: formData,
  }),
  getImportJobs: (limit = 20) => request(`/imports?limit=${limit}`),
  getImportJob: (jobId) => request(`/imports/${jobId}`),
  getImportJobErrors: (jobId, page = 1, pageSize = 20) => request(`/imports/${jobId}/errors?page=${page}&page_size=${pageSize}`),
  // System Maintenance
  clearDatabase: () => request('/system/clear-database', { method: 'POST' }),
  // ABSA (Aspect-Based Sentiment Analysis)
  predictAbsa: (text, savePrediction = false) => request('/absa/predict', {
    method: 'POST',
    body: JSON.stringify({ text, save_prediction: savePrediction }),
  }),
  predictReviewAbsa: (reviewId, savePrediction = true) => request(`/absa/predict/${reviewId}?save_prediction=${savePrediction}`, {
    method: 'POST',
  }),
  getAbsaStatus: () => request('/absa/status'),
  trainAbsaModel: (config = {}) => request('/absa/train', {
    method: 'POST',
    body: JSON.stringify({
      test_size: config.testSize ?? 0.2,
      random_state: config.randomState ?? 42,
      include_seed_dataset: config.includeSeedDataset ?? true,
    }),
  }),
  getAbsaMetrics: () => request('/absa/metrics'),
  annotateReview: (reviewId, annotations) => request(`/absa/annotate/${reviewId}`, {
    method: 'POST',
    body: JSON.stringify({ annotations }),
  }),
  getReviewPredictions: (reviewId) => request(`/absa/predictions/${reviewId}`),
  getAnnotations: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.reviewId) qs.set('review_id', params.reviewId);
    if (params.aspect) qs.set('aspect', params.aspect);
    if (params.status) qs.set('status', params.status);
    if (params.page) qs.set('page', params.page);
    if (params.pageSize) qs.set('page_size', params.pageSize);
    const qStr = qs.toString();
    return request(`/absa/annotations${qStr ? `?${qStr}` : ''}`);
  },
  // Phase 4: Product Recommendations
  getRecommendations: (payload) => request('/recommendations', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getRecommendationAspects: () => request('/recommendations/aspects'),
  getRecommendationProducts: () => request('/recommendations/products'),
  compareProducts: (productIds, priorityAspects = []) => request('/recommendations/compare', {
    method: 'POST',
    body: JSON.stringify({
      product_ids: productIds,
      priority_aspects: priorityAspects,
    }),
  }),
  getProductScores: (productId) => request(`/recommendations/products/${productId}/scores`),
  syncPredictions: (limitPerProduct = 30) => request(`/recommendations/sync-predictions?limit_per_product=${limitPerProduct}`, {
    method: 'POST',
  }),
};


