import { FolderOpen, Settings } from 'lucide-react';

interface HeaderProps {
  onArchiveClick: () => void;
  onSettingsClick: () => void;
}

export function Header({ onArchiveClick, onSettingsClick }: HeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-white border-b border-neutral-200 flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-3">
        <span className="text-xl">📚</span>
        <span className="font-semibold text-neutral-900">HayMAS</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onArchiveClick}
          className="p-2 rounded-lg hover:bg-neutral-100 text-neutral-600 hover:text-neutral-900 transition-colors"
          title="Archiv"
        >
          <FolderOpen size={20} />
        </button>
        <button
          onClick={onSettingsClick}
          className="p-2 rounded-lg hover:bg-neutral-100 text-neutral-600 hover:text-neutral-900 transition-colors"
          title="Einstellungen"
        >
          <Settings size={20} />
        </button>
      </div>
    </header>
  );
}
