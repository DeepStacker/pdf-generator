import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FolderTree, Loader2, CheckCircle2, AlertCircle, AlertTriangle, X } from 'lucide-react';

/**
 * Merge PDF.
 *
 * The operator picks the folder their branches came in -- one subfolder per
 * branch, PDFs inside -- and gets back a zip holding one merged PDF per
 * branch. `/api/merge/upload` does the whole job in a single request and keeps
 * nothing, the same terms as flatten.
 *
 * Two things make this screen different from every other upload here. First,
 * what is uploaded is a *shape*, not a file: the server groups by the folder
 * each PDF sat in, so the path travels alongside every file and the order of
 * the two field lists has to match. Second, the shape is the part that goes
 * wrong -- a branch folder that turns out to be empty, PDFs left loose in the
 * root -- and the operator cannot see that in a file picker. So the reading of
 * the folder is shown before the upload, branch by branch, and the server's
 * notes are shown after it. A branch that was dropped should never be
 * something they discover a week later.
 */

/** One PDF and the path it had inside the picked folder. */
interface PickedFile {
  file: File;
  /** e.g. "Uploaded Folder/Branch A/file1.pdf" -- root segment included. */
  path: string;
}

interface BranchRow {
  name: string;
  count: number;
  /** True when none of its PDFs sit directly in it, only further down. */
  deep: boolean;
}

interface MergeResult {
  name: string;
  branches: string | null;
  sources: string | null;
  pages: string | null;
  bytes: number;
  notes: string[];
}

/* Progress ring geometry: .progress-ring-wrap is 72x72 and already rotates the
   svg -90deg, so the arc starts at twelve o'clock. Same as consolidation. */
const RING_R = 30;
const RING_C = 2 * Math.PI * RING_R;

const isPdf = (name: string) => name.toLowerCase().endsWith('.pdf');

/** Sort "Branch 2" before "Branch 10", which plain alphabetical order does not. */
const naturally = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });

/* --- Reading a dropped folder -------------------------------------------
   A dropped directory arrives as a FileSystemEntry tree rather than a flat
   FileList, and those entries carry no webkitRelativePath -- fullPath is the
   equivalent, minus its leading slash. */

const readDirectory = (dir: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> =>
  new Promise((resolve, reject) => {
    const reader = dir.createReader();
    const all: FileSystemEntry[] = [];
    // readEntries hands back one batch at a time and signals the end with an
    // empty one; calling it once quietly truncates large folders.
    const step = () =>
      reader.readEntries((batch) => {
        if (!batch.length) {
          resolve(all);
          return;
        }
        all.push(...batch);
        step();
      }, reject);
    step();
  });

const fileOf = (entry: FileSystemFileEntry): Promise<File> =>
  new Promise((resolve, reject) => entry.file(resolve, reject));

const walk = async (entry: FileSystemEntry, out: PickedFile[]): Promise<void> => {
  if (entry.isFile) {
    const file = await fileOf(entry as FileSystemFileEntry);
    out.push({ file, path: entry.fullPath.replace(/^\//, '') });
    return;
  }
  if (entry.isDirectory) {
    for (const child of await readDirectory(entry as FileSystemDirectoryEntry)) {
      await walk(child, out);
    }
  }
};

export const TabMerge: React.FC = () => {
  const [picked, setPicked] = useState<PickedFile[]>([]);
  const [ignored, setIgnored] = useState(0);
  const [phase, setPhase] = useState<'idle' | 'reading' | 'uploading' | 'merging'>('idle');
  const [pct, setPct] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MergeResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  /* Folder pickers are a desktop affordance. Several mobile browsers -- iOS
     Safari among them -- have no directory upload at all, and a drop zone
     there would open a file picker that cannot pick what this screen needs. */
  const canPickFolder = useMemo(
    () => typeof document !== 'undefined' && 'webkitdirectory' in document.createElement('input'),
    []
  );

  /* React has no prop for these two, and writing them as unknown JSX
     attributes would not type-check, so they go on after the mount. */
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.setAttribute('webkitdirectory', '');
    el.setAttribute('directory', '');
  }, [canPickFolder]);

  const busy = phase === 'uploading' || phase === 'merging';

  /** What the server will make of this folder, worked out before it is sent. */
  const reading = useMemo(() => {
    const counts = new Map<string, number>();
    // A branch whose PDFs all sit further down is the signature of picking
    // one level too high: root/Region/Branch/file.pdf merges a whole region
    // into one PDF and reports success. Worth saying before the upload, not
    // after it.
    const direct = new Set<string>();
    let loose = 0;
    for (const p of picked) {
      const segs = p.path.split('/').filter(Boolean);
      // segs[0] is the picked folder itself, which the server drops. A PDF
      // with nothing between the two is sitting outside any branch.
      if (segs.length < 3) {
        loose += 1;
        continue;
      }
      counts.set(segs[1], (counts.get(segs[1]) ?? 0) + 1);
      if (segs.length === 3) direct.add(segs[1]);
    }
    const rows: BranchRow[] = [...counts.entries()]
      .map(([name, count]) => ({ name, count, deep: !direct.has(name) }))
      .sort((a, b) => naturally(a.name, b.name));
    return { rows, loose, root: picked[0]?.path.split('/')[0] ?? '' };
  }, [picked]);

  const mergeable = picked.length - reading.loose;

  const accept = (found: PickedFile[]) => {
    const pdfs = found.filter((f) => isPdf(f.file.name));
    setIgnored(found.length - pdfs.length);
    setResult(null);
    if (!pdfs.length) {
      setPicked([]);
      setError('No PDFs in that folder.');
      return;
    }
    setError(null);
    setPicked(pdfs);
  };

  const handlePick = (list: FileList | null) => {
    if (!list || !list.length) return;
    accept(
      Array.from(list).map((file) => ({
        // webkitRelativePath is the whole point of the directory picker; the
        // bare name is a last resort for a browser that leaves it empty.
        file,
        path: file.webkitRelativePath || file.name,
      }))
    );
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (busy) return;

    // The item list goes stale the moment this handler yields, so the entries
    // are taken up front and only then walked.
    const entries = Array.from(e.dataTransfer.items)
      .map((item) => item.webkitGetAsEntry())
      .filter((entry): entry is FileSystemEntry => !!entry);

    if (!entries.some((entry) => entry.isDirectory)) {
      setError('Drop the folder that holds your branch folders, not the PDFs themselves.');
      return;
    }

    setPhase('reading');
    try {
      const found: PickedFile[] = [];
      for (const entry of entries) await walk(entry, found);
      accept(found);
    } catch {
      setError('That folder could not be read.');
    } finally {
      setPhase('idle');
    }
  };

  const clear = () => {
    setPicked([]);
    setIgnored(0);
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const run = () => {
    if (!picked.length || busy) return;
    setError(null);
    setResult(null);
    setPct(0);
    setPhase('uploading');

    const body = new FormData();
    // One `path` per `file`, appended in step so the two lists line up on the
    // far side -- the server zips them positionally.
    for (const p of picked) {
      body.append('file', p.file, p.file.name);
      body.append('path', p.path);
    }

    // fetch() cannot report upload progress, and a folder of branch reports is
    // the one upload here big enough for that to matter.
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/merge/upload');
    xhr.responseType = 'blob';

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) setPct((ev.loaded / ev.total) * 100);
    };
    // Everything after the last byte is the server merging, which has no
    // progress to report -- so say that rather than sit at 100%.
    xhr.upload.onload = () => {
      setPct(100);
      setPhase('merging');
    };

    xhr.onload = () => {
      void (async () => {
        try {
          const blob: Blob = xhr.response;
          if (xhr.status !== 200) {
            let detail = `Merge failed (HTTP ${xhr.status})`;
            try {
              const payload = JSON.parse(await blob.text());
              if (payload?.detail) detail = payload.detail;
            } catch {
              /* the body was not JSON; the status line is all we have */
            }
            setError(detail);
            return;
          }

          const name = `${(reading.root || 'Merged').replace(/[<>:"/\\|?*]/g, '_')}_Merged.zip`;

          // Notes are the whole reason a dropped branch is not a silent loss,
          // so a header the server had to truncate still says something.
          let notes: string[] = [];
          const raw = xhr.getResponseHeader('X-Merge-Notes');
          try {
            const parsed = raw ? JSON.parse(raw) : [];
            if (Array.isArray(parsed)) notes = parsed.map(String);
          } catch {
            notes = ['The server reported notes about this folder, but they were too long to read back.'];
          }

          // Recorded before the download is triggered, not after: the server
          // keeps no copy, so if a browser refuses the save the counts and the
          // notes are the only account of the run left.
          setResult({
            name,
            branches: xhr.getResponseHeader('X-Merge-Branches'),
            sources: xhr.getResponseHeader('X-Merge-Sources'),
            pages: xhr.getResponseHeader('X-Merge-Pages'),
            bytes: blob.size,
            notes,
          });

          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = name;
          a.click();
          URL.revokeObjectURL(url);
        } finally {
          setPhase('idle');
        }
      })();
    };

    xhr.onerror = () => {
      setError('Could not reach the server.');
      setPhase('idle');
    };
    xhr.onabort = () => setPhase('idle');

    xhr.send(body);
  };

  const sizeLabel = (bytes: number) =>
    bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;

  return (
    <div className="space-y-6">
      <div className="section-header">
        <div>
          <h2 className="section-title">Merge PDF</h2>
          <p className="text-xs text-slate-400 mt-1">
            One folder of branches in, one merged PDF per branch out, together in a zip.
          </p>
        </div>
        <span className="section-badge badge-emerald">Nothing Stored</span>
      </div>

      <div className="card space-y-4 max-w-3xl mx-auto">
        <p className="text-xs text-slate-400 leading-relaxed">
          Pick the folder that holds one subfolder per branch. Every PDF inside a branch is merged
          into a single <span className="font-mono text-slate-300">Branch.pdf</span>, in natural file
          order, and the results come back as one zip. The uploaded folder and the zip are both
          removed from the server as soon as the download is sent.
        </p>

        <div>
          <label className="field-label">Branch Folder</label>

          {canPickFolder ? (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  inputRef.current?.click();
                }
              }}
              role="button"
              tabIndex={0}
              className={`drop-zone ${dragging ? 'dragover' : ''}`}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handlePick(e.target.files)}
              />
              <FolderTree className="drop-zone-icon w-7 h-7" />
              <span className="drop-zone-title">
                {phase === 'reading' ? 'Reading the folder…' : 'Drop the branch folder here, or click to browse'}
              </span>
              <span className="drop-zone-sub">One subfolder per branch · .pdf files only</span>
            </div>
          ) : (
            /* Not an error -- this browser simply has no folder picker, and a
               control that cannot do the job is worse than none. */
            <div className="validation-box flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <span className="text-slate-300">
                This browser cannot upload a folder — several mobile browsers, including Safari on
                iOS, have no folder picker. Open this screen on a desktop browser to merge.
              </span>
            </div>
          )}
        </div>

        {picked.length > 0 && (
          <div className="space-y-3">
            <div className="file-row">
              <span className="text-xs font-semibold text-slate-200 truncate" title={reading.root}>
                {reading.root || 'Selected folder'}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-2xs font-mono text-slate-500">
                  {mergeable} PDF{mergeable === 1 ? '' : 's'} · {reading.rows.length} branch
                  {reading.rows.length === 1 ? '' : 'es'}
                </span>
                <button
                  onClick={clear}
                  disabled={busy}
                  className="btn btn-ghost btn-sm"
                  aria-label="Clear selected folder"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* What the server is about to see, so a mis-shaped folder is
                caught here rather than in the notes afterwards. */}
            {reading.rows.length > 0 && (
              <div className="overflow-x-auto">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Branch</th>
                      <th>PDFs</th>
                      <th>Merges Into</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reading.rows.map((row) => (
                      <tr key={row.name}>
                        <td className="truncate" title={row.name}>{row.name}</td>
                        <td className="font-mono">
                          {row.count}
                          {row.deep && <span className="text-amber-400"> ↓</span>}
                        </td>
                        <td className="font-mono text-slate-400 truncate">{row.name}.pdf</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {reading.rows.length === 0 && (
              <div className="validation-box flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span className="text-slate-300">
                  Every PDF sits directly in that folder, with no branch subfolders — there is
                  nothing to group. Pick the folder one level up.
                </span>
              </div>
            )}

            {reading.rows.length > 0 && reading.rows.every((row) => row.deep) && (
              <div className="validation-box flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span className="text-slate-300">
                  Every PDF sits one level further down than expected, so each folder above would be
                  merged into a single PDF. If{' '}
                  <span className="font-mono text-slate-200">{reading.rows[0].name}</span> holds your
                  branches rather than being one, pick the folder one level down.
                </span>
              </div>
            )}

            {(reading.loose > 0 || ignored > 0) && reading.rows.length > 0 && (
              <div className="validation-box flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <span className="text-slate-300">
                  {reading.loose > 0 && (
                    <>
                      {reading.loose} PDF{reading.loose === 1 ? '' : 's'} sat outside any branch and
                      will be skipped.{' '}
                    </>
                  )}
                  {ignored > 0 && (
                    <>
                      {ignored} non-PDF file{ignored === 1 ? '' : 's'} in that folder{' '}
                      {ignored === 1 ? 'was' : 'were'} left out.
                    </>
                  )}
                </span>
              </div>
            )}
          </div>
        )}

        {/* The single place a failure shows up, so it stays next to the button. */}
        {error && (
          <div className="validation-box flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span className="text-rose-400">{error}</span>
          </div>
        )}

        {busy && (
          <div className="progress-container">
            <div className="progress-ring-wrap">
              <svg width="72" height="72">
                <circle
                  cx="36" cy="36" r={RING_R} fill="transparent" strokeWidth="6"
                  style={{ stroke: 'var(--bg-elevated)' }}
                />
                <circle
                  cx="36" cy="36" r={RING_R} fill="transparent" strokeWidth="6" strokeLinecap="round"
                  strokeDasharray={RING_C}
                  strokeDashoffset={RING_C * (1 - Math.min(Math.max(pct, 0), 100) / 100)}
                  style={{ stroke: 'var(--accent-blue)', transition: 'stroke-dashoffset 250ms ease' }}
                />
              </svg>
              <span className="progress-pct">{Math.round(pct)}%</span>
            </div>
            <div className="min-w-0">
              <span className="block text-xs font-bold text-slate-200 truncate">
                {phase === 'merging' ? 'Merging on the server…' : 'Uploading the folder…'}
              </span>
              <span className="block text-xs text-slate-400 mt-1">
                {mergeable} PDF{mergeable === 1 ? '' : 's'} across {reading.rows.length} branch
                {reading.rows.length === 1 ? '' : 'es'}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={run}
          disabled={!picked.length || reading.rows.length === 0 || busy}
          className="btn btn-primary w-full"
        >
          {busy ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{phase === 'merging' ? 'Merging…' : 'Uploading…'}</span>
            </>
          ) : (
            'Merge Branches'
          )}
        </button>

        {result && (
          <div className="space-y-3">
            <div className="validation-box flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span className="text-slate-300 truncate">
                Downloaded <span className="font-mono text-slate-200">{result.name}</span>
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                ['Branches', result.branches ?? '—'],
                ['Source PDFs', result.sources ?? '—'],
                ['Pages', result.pages ?? '—'],
                ['Size', sizeLabel(result.bytes)],
              ].map(([label, value]) => (
                <div key={label} className="stat-card">
                  <span className="stat-label">{label}</span>
                  <span className="stat-value font-mono">{value}</span>
                </div>
              ))}
            </div>

            {/* A branch the server dropped is the one thing that must not go
                unread, so the notes get their own block rather than a line. */}
            {result.notes.length > 0 && (
              <div className="validation-box space-y-2">
                <span className="flex items-center gap-2 text-xs font-semibold text-amber-400">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  {result.notes.length} note{result.notes.length === 1 ? '' : 's'} about this folder
                </span>
                <ul className="space-y-1">
                  {result.notes.map((note, i) => (
                    <li key={i} className="text-xs text-slate-300 leading-relaxed">
                      • {note}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
