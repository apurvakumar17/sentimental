import React, { useState, useEffect } from 'react';
import { Search, Filter, Smartphone, ChevronLeft, ChevronRight, SlidersHorizontal, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import ReviewCard from './ReviewCard';

export default function ReviewExplorer({ products }) {
  const [reviews, setReviews] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [minRating, setMinRating] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const loadReviews = async () => {
    setIsLoading(true);
    try {
      const data = await api.getReviews({
        productId: selectedProduct || undefined,
        minRating: minRating || undefined,
        q: searchQuery || undefined,
        page,
        pageSize: 6,
      });
      setReviews(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.pages || 1);
    } catch (err) {
      console.error('Failed to fetch reviews:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReviews();
  }, [page, selectedProduct, minRating]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadReviews();
  };

  return (
    <div className="space-y-5">
      {/* Search & Filter Header */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-xl shadow-2xl">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Keyword Search */}
          <div className="sm:col-span-6 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search keyword in reviews, titles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          {/* Product Filter */}
          <div className="sm:col-span-3">
            <select
              value={selectedProduct}
              onChange={(e) => {
                setSelectedProduct(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Smartphone Models</option>
              {products?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.review_count})
                </option>
              ))}
            </select>
          </div>

          {/* Rating Filter */}
          <div className="sm:col-span-3 flex space-x-2">
            <select
              value={minRating}
              onChange={(e) => {
                setMinRating(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Ratings</option>
              <option value="4.5">★ 4.5 & Above</option>
              <option value="4.0">★ 4.0 & Above</option>
              <option value="3.0">★ 3.0 & Above</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-colors flex items-center justify-center flex-shrink-0"
              title="Refresh search"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </form>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-800/60 text-xs text-slate-400">
          <span>
            Found <strong className="text-white">{total}</strong> verified reviews
          </span>
          {isLoading && (
            <span className="flex items-center space-x-1 text-indigo-400">
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Fetching...</span>
            </span>
          )}
        </div>
      </div>

      {/* Reviews Grid */}
      {reviews.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center backdrop-blur-md">
          <Smartphone className="w-10 h-10 text-slate-400 mx-auto mb-3" />
          <h4 className="text-base font-semibold text-slate-300">No reviews found</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Try adjusting your search criteria or launch a scraping job to collect reviews.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reviews.map((rev) => (
            <ReviewCard key={rev.id} review={rev} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <span className="text-xs text-slate-400 font-mono">
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isLoading}
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40 transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
