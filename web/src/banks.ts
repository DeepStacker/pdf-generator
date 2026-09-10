import type React from 'react';

/**
 * The banks, in one place.
 *
 * The sidebar lists them and the audit screen renders whichever is selected,
 * so a bank's name, dot colour and accent are defined once rather than kept
 * in step by hand. `fill` is the AA-safe darker tier -- white text sits on it,
 * and the lighter dot colour fails contrast there.
 */
export interface BankMeta {
  name: string;
  short: string;
  /** Sidebar text. Kept identical to the desktop's, which is why it is not
      simply `label` -- that one is the header badge and reads differently. */
  nav: string;
  label: string;
  desc: string;
  dot: string;
  fill: string;
  badge: string;
  runClass: string;
  runStyle?: React.CSSProperties;
}

export const BANKS: BankMeta[] = [
  {
    name: 'IDFC First Bank',
    nav: 'IDFC First Bank',
    short: 'IDFC FIRST',
    label: 'IDFC FIRST Bank',
    desc: 'Physical verification and Touch & Feel branch reports, straight from the master audit sheet.',
    dot: '#4c6fff',
    fill: 'var(--accent-blue-fill)',
    badge: 'badge-blue',
    runClass: 'btn-primary',
  },
  {
    name: 'Equitas Small Finance Bank',
    nav: 'Equitas Small Finance',
    short: 'Equitas',
    label: 'Equitas Small Finance Bank',
    desc: 'Single-packet audit reports, then consolidate them into one branch bundle.',
    dot: '#c7841f',
    fill: 'var(--accent-amber-fill)',
    badge: 'badge-amber',
    runClass: 'btn-primary',
    runStyle: { background: 'var(--accent-amber-fill)' },
  },
  {
    name: 'Arvog Bank',
    nav: 'Arvog Bank',
    short: 'Arvog',
    label: 'Arvog Bank',
    desc: 'Branch and packet-wise PDF groupings, straight from the master audit sheet.',
    dot: '#34c98c',
    fill: 'var(--accent-emerald-fill)',
    badge: 'badge-emerald',
    runClass: 'btn-success',
  },
];

