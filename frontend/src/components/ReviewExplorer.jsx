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
      <div className="rounded-2xl border border-[#12544F]/60 bg-[#071b1f]/95 p-5 backdrop-blur-xl shadow-2xl">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Keyword Search */}
          <div className="sm:col-span-6 relative">
            <Search className="w-4 h-4 text-[#8BBB92] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search keyword in reviews, titles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-[#030c0e] border border-[#12544F]/70 rounded-xl text-sm text-[#f2fbf6] placeholder-[#649182] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
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
              className="w-full px-3 py-2.5 bg-[#030c0e] border border-[#12544F]/70 rounded-xl text-sm text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
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
              className="w-full px-3 py-2.5 bg-[#030c0e] border border-[#12544F]/70 rounded-xl text-sm text-[#f2fbf6] focus:outline-none focus:border-[#2A835F] focus:ring-1 focus:ring-[#2A835F] transition-colors"
            >
              <option value="">All Ratings</option>
              <option value="4.5">★ 4.5 & Above</option>
              <option value="4.0">★ 4.0 & Above</option>
              <option value="3.0">★ 3.0 & Above</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2.5 bg-[#2A835F] hover:bg-[#329b71] text-white rounded-xl text-sm font-semibold transition-colors flex items-center justify-center flex-shrink-0 shadow-md shadow-[#2A835F]/20 active:scale-[0.98]"
              title="Refresh search"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </form>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#12544F]/50 text-xs text-[#7ea698]">
          <span>
            Found <strong className="text-white">{total}</strong> verified reviews
          </span>
          {isLoading && (
            <span className="flex items-center space-x-1 text-[#8BBB92]">
              <RefreshCw className="w-3 h-3 animate-spin" />
              <span>Fetching...</span>
            </span>
          )}
        </div>
      </div>

      {/* Reviews Grid */}
      {reviews.length === 0 ? (
        <div className="rounded-2xl border border-[#12544F]/40 bg-[#071b1f]/50 p-12 text-center backdrop-blur-md">
          <Smartphone className="w-10 h-10 text-[#649182] mx-auto mb-3" />
          <h4 className="text-base font-semibold text-[#f2fbf6]">No reviews found</h4>
          <p className="text-xs text-[#7ea698] mt-1 max-w-sm mx-auto">
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
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-[#030c0e] border border-[#12544F]/70 text-sm text-[#8BBB92] hover:bg-[#12544F]/30 hover:text-white disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <span className="text-xs text-[#7ea698]">
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isLoading}
            className="flex items-center space-x-1 px-4 py-2 rounded-xl bg-[#030c0e] border border-[#12544F]/70 text-sm text-[#8BBB92] hover:bg-[#12544F]/30 hover:text-white disabled:opacity-40 transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
