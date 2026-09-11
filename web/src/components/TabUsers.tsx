import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  KeyRound,
  Shield,
  ShieldOff,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react';

export interface UserAccount {
  username: string;
  is_admin: boolean;
  created_at: string;
}

interface TabUsersProps {
  /** Who is signed in. Only used to mark "you" in the list -- the server, not
   *  this screen, decides what you may do to your own account. */
  currentUser: string | null;
}

/** Every account endpoint answers the same shape, success or failure. */
type Outcome = { ok: true; message: string } | { ok: false; error: string };

/**
 * The rules (12-character passwords, the last admin, your own account) live in
 * the server and are enforced there. This reads whatever it said and hands it
 * back verbatim rather than second-guessing it, so the screen cannot drift out
 * of step with the rule it is describing.
 */
async function callApi(url: string, init?: RequestInit): Promise<Outcome> {
  try {
    const res = await fetch(url, init);
    const data = await res.json().catch(() => ({} as any));
    if (res.ok && data.success) return { ok: true, message: data.message || 'Done.' };
    return { ok: false, error: data.error || data.message || `Request failed (${res.status}).` };
  } catch {
    return { ok: false, error: 'Could not reach the server.' };
  }
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/** created_at is an ISO timestamp; nobody reads one of those at a glance. */
const formatCreated = (raw: string): string => {
  if (!raw) return '--';
  const when = new Date(raw);
  if (Number.isNaN(when.getTime())) return raw;
  return when.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
};

/* .section-badge's geometry, inline. The shared mobile layer hides
   .section-badge outright -- it is written for the badge in a page header,
   which the top bar already says -- and whether an account is an admin still
   has to be readable at 375px. The colour still comes from the shared set. */
const BADGE: React.CSSProperties = {
  display: 'inline-block',
  padding: '0.2rem 0.6rem',
  borderRadius: '99px',
  fontSize: '0.68rem',
  fontWeight: 700,
  whiteSpace: 'nowrap',
};

const Failure: React.FC<{ text: string }> = ({ text }) => (
  <div className="validation-box flex items-start gap-2">
    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
    <span className="text-rose-400">{text}</span>
  </div>
);

export const TabUsers: React.FC<TabUsersProps> = ({ currentUser }) => {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  /** Result of the last action taken outside a dialog. */
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  // --- Add an account ---
  const [newName, setNewName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // --- Dialogs. Each carries its own error, shown where the action was taken. ---
  const [resetFor, setResetFor] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [confirming, setConfirming] = useState<{ kind: 'remove' | 'demote'; username: string } | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);

  /** Name of the action in flight, so exactly one button can show it. */
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/users');
      const data = await res.json().catch(() => ({} as any));
      if (res.ok && data.success && Array.isArray(data.users)) {
        setUsers(data.users);
        setLoadError(null);
      } else {
        setUsers([]);
        setLoadError(data.error || `Could not load accounts (${res.status}).`);
      }
    } catch {
      setUsers([]);
      setLoadError('Could not reach the server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const closeDialogs = () => {
    setResetFor(null);
    setResetPassword('');
    setConfirming(null);
    setDialogError(null);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError(null);
    setNotice(null);
    setBusy('add');
    const result = await callApi('/api/users', jsonPost({
      username: newName,
      password: newPassword,
      is_admin: newIsAdmin,
    }));
    setBusy(null);
    if (!result.ok) {
      setAddError(result.error);
      return;
    }
    setNewName('');
    setNewPassword('');
    setNewIsAdmin(false);
    setNotice({ ok: true, text: result.message });
    load();
  };

  /** Promoting is not destructive, so it happens straight from the row. */
  const handlePromote = async (username: string) => {
    setNotice(null);
    setBusy(`admin:${username}`);
    const result = await callApi(`/api/users/${encodeURIComponent(username)}/admin`, jsonPost({ is_admin: true }));
    setBusy(null);
    setNotice({ ok: result.ok, text: result.ok ? result.message : result.error });
    if (result.ok) load();
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetFor) return;
    setDialogError(null);
    setBusy('reset');
    const result = await callApi(`/api/users/${encodeURIComponent(resetFor)}/password`, jsonPost({ password: resetPassword }));
    setBusy(null);
    if (!result.ok) {
      setDialogError(result.error);
      return;
    }
    setNotice({ ok: true, text: result.message });
    closeDialogs();
    load();
  };

  const handleConfirm = async () => {
    if (!confirming) return;
    const { kind, username } = confirming;
    setDialogError(null);
    setBusy('confirm');
    const result = kind === 'remove'
      ? await callApi(`/api/users/${encodeURIComponent(username)}`, { method: 'DELETE' })
      : await callApi(`/api/users/${encodeURIComponent(username)}/admin`, jsonPost({ is_admin: false }));
    setBusy(null);
    if (!result.ok) {
      setDialogError(result.error);
      return;
    }
    setNotice({ ok: true, text: result.message });
    closeDialogs();
    load();
  };

  const isYou = (username: string) => !!currentUser && username === currentUser.toLowerCase();

  return (
    <div className="space-y-6">
      <div className="section-header">
        <div>
          <h2 className="section-title">Users</h2>
          <p className="text-sm text-slate-400 mt-1">
            Accounts that can sign in to this server, and who among them may manage the rest.
          </p>
        </div>
      </div>

      {notice && (
        notice.ok ? (
          <div className="validation-box flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
            <span className="text-emerald-400">{notice.text}</span>
          </div>
        ) : (
          <Failure text={notice.text} />
        )
      )}

      {loadError && <Failure text={loadError} />}

      {/* The account list. The empty and loading states are deliberately not
          rows inside the table: four columns force it wider than a phone, so a
          centred cell spanning them all sits off the right edge. */}
      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
          <p className="text-slate-500 italic">Loading accounts...</p>
        </div>
      ) : users.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
          <p className="text-slate-500 italic">
            {loadError ? 'No accounts could be listed.' : 'No accounts yet.'}
          </p>
        </div>
      ) : (
        <div className="card card-flush">
          <div className="overflow-x-auto">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Created</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.username}>
                    <td className="font-mono font-semibold">
                      {user.username}
                      {/* Tailwind's margin utilities lose to the shared sheet's
                          own `* { margin: 0 }`, which is unlayered; only the
                          handful web.css redefines (mt-1, mt-2...) survive. */}
                      {isYou(user.username) && (
                        <span className="text-2xs text-slate-500" style={{ marginLeft: '0.5rem' }}>you</span>
                      )}
                    </td>
                    <td>
                      <span className={user.is_admin ? 'badge-emerald' : 'badge-blue'} style={BADGE}>
                        {user.is_admin ? 'Admin' : 'Member'}
                      </span>
                    </td>
                    <td className="font-mono text-slate-400">{formatCreated(user.created_at)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => {
                            setDialogError(null);
                            setResetPassword('');
                            setResetFor(user.username);
                          }}
                        >
                          <KeyRound className="w-3 h-3" />
                          <span>Password</span>
                        </button>

                        {/* Demoting can lock everyone out of account management,
                            so it goes through a confirmation; promoting cannot. */}
                        {user.is_admin ? (
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => {
                              setDialogError(null);
                              setConfirming({ kind: 'demote', username: user.username });
                            }}
                          >
                            <ShieldOff className="w-3 h-3" />
                            <span>Revoke admin</span>
                          </button>
                        ) : (
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={busy === `admin:${user.username}`}
                            onClick={() => handlePromote(user.username)}
                          >
                            <Shield className="w-3 h-3" />
                            <span>Make admin</span>
                          </button>
                        )}

                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => {
                            setDialogError(null);
                            setConfirming({ kind: 'remove', username: user.username });
                          }}
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Remove</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* --- Add an account --- */}
      <form className="card space-y-4" onSubmit={handleAdd}>
        <div>
          <h3 className="stat-label">Add an Account</h3>
          <p className="text-2xs text-slate-500 mt-1">
            The new account can sign in straight away with the password you set here.
          </p>
        </div>

        <div className="grid grid-2 gap-4">
          <div>
            <label className="field-label" htmlFor="newUsername">Username</label>
            <input
              id="newUsername"
              type="text"
              className="input-field"
              placeholder="e.g. priya.n"
              autoComplete="off"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <p className="text-2xs text-slate-500 mt-2">
              Letters, digits, dot, dash or underscore. Stored in lower case.
            </p>
          </div>

          <div>
            <label className="field-label" htmlFor="newPassword">Password</label>
            <input
              id="newPassword"
              type="password"
              className="input-field"
              placeholder="At least 12 characters"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <p className="text-2xs text-slate-500 mt-2">
              This server faces the internet, so 12 characters is the floor.
            </p>
          </div>
        </div>

        <label htmlFor="newIsAdmin" className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            id="newIsAdmin"
            checked={newIsAdmin}
            onChange={(e) => setNewIsAdmin(e.target.checked)}
          />
          <span className="text-xs text-slate-300">
            Make this account an admin, able to manage every other account
          </span>
        </label>

        {addError && <Failure text={addError} />}

        <div
          className="flex justify-end"
          style={{ paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}
        >
          <button type="submit" className="btn btn-primary btn-sm" disabled={busy === 'add'}>
            <UserPlus className="w-4 h-4" />
            <span>{busy === 'add' ? 'Adding...' : 'Add Account'}</span>
          </button>
        </div>
      </form>

      {/* --- Reset a password --- */}
      {resetFor && (
        <div className="modal-overlay">
          <form className="modal-box" onSubmit={handleResetPassword}>
            <div className="modal-header">
              <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
                <KeyRound className="w-5 h-5 text-blue-400" />
                <div style={{ minWidth: 0 }}>
                  <h3>Reset password</h3>
                  <p className="text-2xs font-mono text-slate-400 mt-1 truncate">{resetFor}</p>
                </div>
              </div>
              <button type="button" onClick={closeDialogs} className="btn btn-ghost btn-sm" aria-label="Close">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="modal-body space-y-4">
              <div>
                <label className="field-label" htmlFor="resetPassword">New password</label>
                <input
                  id="resetPassword"
                  type="password"
                  className="input-field"
                  placeholder="At least 12 characters"
                  autoComplete="new-password"
                  autoFocus
                  value={resetPassword}
                  onChange={(e) => setResetPassword(e.target.value)}
                />
              </div>
              <p className="text-2xs text-slate-500">
                The old password stops working immediately. Anyone already signed in stays signed in.
              </p>
              {dialogError && <Failure text={dialogError} />}
            </div>

            <div className="modal-footer">
              <button type="button" onClick={closeDialogs} className="btn btn-ghost btn-sm">Cancel</button>
              <button type="submit" className="btn btn-primary btn-sm" disabled={busy === 'reset'}>
                {busy === 'reset' ? 'Saving...' : 'Set Password'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- Confirm a destructive change --- */}
      {confirming && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
                {confirming.kind === 'remove'
                  ? <Trash2 className="w-5 h-5" style={{ color: 'var(--accent-rose)' }} />
                  : <ShieldOff className="w-5 h-5" style={{ color: 'var(--accent-rose)' }} />}
                <div style={{ minWidth: 0 }}>
                  <h3>{confirming.kind === 'remove' ? 'Remove account' : 'Revoke admin'}</h3>
                  <p className="text-2xs font-mono text-slate-400 mt-1 truncate">{confirming.username}</p>
                </div>
              </div>
              <button onClick={closeDialogs} className="btn btn-ghost btn-sm" aria-label="Close">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="modal-body space-y-4">
              <p className="text-sm text-slate-300">
                {confirming.kind === 'remove' ? (
                  <>
                    <span className="font-mono font-semibold">{confirming.username}</span> will no
                    longer be able to sign in. This cannot be undone -- the account has to be
                    created again, with a new password.
                  </>
                ) : (
                  <>
                    <span className="font-mono font-semibold">{confirming.username}</span> keeps
                    their account and can still sign in, but will no longer be able to manage
                    accounts -- including their own.
                  </>
                )}
              </p>
              {dialogError && <Failure text={dialogError} />}
            </div>

            <div className="modal-footer">
              <button onClick={closeDialogs} className="btn btn-ghost btn-sm">Cancel</button>
              <button onClick={handleConfirm} className="btn btn-danger btn-sm" disabled={busy === 'confirm'}>
                {busy === 'confirm'
                  ? 'Working...'
                  : confirming.kind === 'remove' ? 'Remove Account' : 'Revoke Admin'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
