import { X, FileText, Download, FileDown, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Article } from '../types';
import { getArticles, deleteArticle, downloadArticleMd, downloadArticlePdf } from '../lib/api';

interface ArchiveDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelectArticle: (article: Article) => void;
}

export function ArchiveDrawer({ open, onClose, onSelectArticle }: ArchiveDrawerProps) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);

  const loadArticles = () => {
    setLoading(true);
    getArticles()
      .then((data) => setArticles(data || []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (open) {
      loadArticles();
    }
  }, [open]);

  const handleDelete = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Artikel "${filename}" wirklich löschen?`)) return;
    
    setDeletingFile(filename);
    try {
      await deleteArticle(filename);
      loadArticles(); // Liste neu laden
    } catch (error) {
      alert('Löschen fehlgeschlagen');
    } finally {
      setDeletingFile(null);
    }
  };

  const handleDownloadMd = (filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    downloadArticleMd(filename);
  };

  const handleDownloadPdf = (filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    downloadArticlePdf(filename);
  };

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
                <div
                  key={article.filename}
                  className="p-3 rounded-lg hover:bg-neutral-50 border border-neutral-200 transition-colors"
                >
                  {/* Artikel-Titel (klickbar) */}
                  <button
                    onClick={() => onSelectArticle(article)}
                    className="w-full text-left"
                  >
                    <div className="font-medium text-neutral-900 text-sm truncate">
                      {article.title}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1">
                      {new Date(article.modified).toLocaleDateString('de-DE')}
                    </div>
                  </button>
                  
                  {/* Action Buttons */}
                  <div className="flex items-center gap-1 mt-2 pt-2 border-t border-neutral-100">
                    <button
                      onClick={(e) => handleDownloadMd(article.filename, e)}
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs text-neutral-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Markdown herunterladen"
                    >
                      <Download size={14} />
                      MD
                    </button>
                    <button
                      onClick={(e) => handleDownloadPdf(article.filename, e)}
                      className="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs text-neutral-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="PDF exportieren"
                    >
                      <FileDown size={14} />
                      PDF
                    </button>
                    <button
                      onClick={(e) => handleDelete(article.filename, e)}
                      disabled={deletingFile === article.filename}
                      className="flex items-center justify-center p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                      title="Löschen"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
