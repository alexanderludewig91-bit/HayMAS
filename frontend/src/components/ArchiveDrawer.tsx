import { X, FileText } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Article } from '../types';
import { getArticles } from '../lib/api';

interface ArchiveDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelectArticle: (article: Article) => void;
}

export function ArchiveDrawer({ open, onClose, onSelectArticle }: ArchiveDrawerProps) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      getArticles()
        .then((data) => setArticles(data || []))
        .catch(() => setArticles([]))
        .finally(() => setLoading(false));
    }
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-80 bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <h2 className="font-semibold text-neutral-900">Archiv</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 text-neutral-500"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-center text-neutral-500 py-8">Laden...</div>
          ) : articles.length === 0 ? (
            <div className="text-center text-neutral-500 py-8">
              <FileText size={32} className="mx-auto mb-2 opacity-50" />
              <p>Noch keine Artikel</p>
            </div>
          ) : (
            <div className="space-y-2">
              {articles.map((article) => (
                <button
                  key={article.filename}
                  onClick={() => onSelectArticle(article)}
                  className="w-full text-left p-3 rounded-lg hover:bg-neutral-50 border border-neutral-200 transition-colors"
                >
                  <div className="font-medium text-neutral-900 text-sm truncate">
                    {article.title}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    {new Date(article.modified).toLocaleDateString('de-DE')}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
