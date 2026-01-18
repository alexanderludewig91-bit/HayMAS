import { useState, useEffect } from 'react';
import { Download, Plus, CheckCircle, FileText, FileDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { LogDrawer } from './LogDrawer';
import { getArticleLog, type SessionLog } from '../lib/api';

interface CompleteViewProps {
  articleContent: string | null;
  articlePath: string | null;
  onReset: () => void;
}

export function CompleteView({ articleContent, articlePath, onReset }: CompleteViewProps) {
  const [logDrawerOpen, setLogDrawerOpen] = useState(false);
  const [log, setLog] = useState<SessionLog | null>(null);
  const [logLoading, setLogLoading] = useState(false);
  const [pdfGenerating, setPdfGenerating] = useState(false);

  const handleDownload = () => {
    if (!articleContent) return;

    const blob = new Blob([articleContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = articlePath?.split('/').pop() || 'artikel.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleShowLog = async () => {
    setLogDrawerOpen(true);
    if (!log && articlePath) {
      setLogLoading(true);
      const filename = articlePath.split('/').pop() || '';
      const fetchedLog = await getArticleLog(filename);
      setLog(fetchedLog);
      setLogLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!articlePath) return;

    setPdfGenerating(true);

    try {
      const filename = articlePath.split('/').pop() || 'artikel.md';
      const response = await fetch(`http://localhost:8000/api/articles/${filename}/pdf`);
      
      if (!response.ok) {
        throw new Error('PDF-Generierung fehlgeschlagen');
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.replace('.md', '.pdf');
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF-Generierung fehlgeschlagen:', error);
    } finally {
      setPdfGenerating(false);
    }
  };

  // Log laden wenn Artikel sich ändert
  useEffect(() => {
    setLog(null);
  }, [articlePath]);

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-neutral-200">
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircle size={20} />
          <span className="font-medium">Artikel fertig</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleShowLog}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
          >
            <FileText size={16} />
            Details
          </button>
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 transition-colors"
          >
            <Plus size={16} />
            Neuer Artikel
          </button>
          <button
            onClick={handleDownload}
            disabled={!articleContent}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors disabled:opacity-50"
          >
            <Download size={16} />
            Markdown
          </button>
          <button
            onClick={handleDownloadPDF}
            disabled={!articlePath || pdfGenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-emerald-200 bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 transition-colors disabled:opacity-50"
          >
            <FileDown size={16} className={pdfGenerating ? 'animate-pulse' : ''} />
            {pdfGenerating ? 'Generiere...' : 'PDF'}
          </button>
        </div>
      </div>

      {/* Log Drawer */}
      <LogDrawer
        open={logDrawerOpen}
        onClose={() => setLogDrawerOpen(false)}
        log={log}
        loading={logLoading}
      />

      {/* Article */}
      <div className="flex-1 overflow-y-auto">
        {articleContent ? (
          <article className="prose prose-neutral max-w-none">
            <ReactMarkdown>{articleContent}</ReactMarkdown>
          </article>
        ) : (
          <div className="text-center text-neutral-500 py-12">
            Kein Artikelinhalt verfügbar
          </div>
        )}
      </div>
    </div>
  );
}
