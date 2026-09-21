'use client';
import { ReactNode } from 'react';
import clsx from 'clsx';

// ── Card ──────────────────────────────────────────────────────────────────
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div 
      className={clsx(
        'rounded-lg border border-border bg-surface',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">
      {children}
    </p>
  );
}

// ── MetricCard ───────────────────────────────────────────────────────────
export function MetricCard({
  title, value, change,
}: {
  title: string;
  value: string | number;
  change?: { value: number; positive: boolean };
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-text-muted">{title}</p>
        {change && (
          <span className={clsx(
            'text-xs font-medium',
            change.positive ? 'text-accent-success' : 'text-accent-danger'
          )}>
            {change.positive ? '+' : ''}{change.value}%
          </span>
        )}
      </div>
      <p className="font-mono text-xl font-semibold text-text-primary">{value}</p>
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────
const badgeVariants = {
  success: 'bg-accent-success/10 text-accent-success border-accent-success/20',
  danger:  'bg-accent-danger/10 text-accent-danger border-accent-danger/20',
  warning: 'bg-accent-warning/10 text-accent-warning border-accent-warning/20',
  primary: 'bg-accent-primary/10 text-accent-primary border-accent-primary/20',
  muted:   'bg-border text-text-muted',
} as const;

export function Badge({
  children, variant = 'primary',
}: {
  children: ReactNode; 
  variant?: keyof typeof badgeVariants;
}) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
      badgeVariants[variant]
    )}>
      {children}
    </span>
  );
}

// ── Button ────────────────────────────────────────────────────────────────
export function Button({
  children, onClick, disabled, variant = 'primary', size = 'md', className,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md';
  className?: string;
}) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'inline-flex items-center gap-2 font-medium rounded-md transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        sizeClasses[size],
        variant === 'primary'   && 'bg-accent-primary text-white hover:bg-accent-primary/90',
        variant === 'secondary' && 'bg-surface border border-border text-text-secondary hover:bg-surface-hover',
        variant === 'ghost'     && 'text-text-muted hover:text-text-primary hover:bg-surface/50',
        className,
      )}
    >
      {children}
    </button>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────
export function Spinner() {
  return <span className="spinner" />;
}

// ── LoadingBox ────────────────────────────────────────────────────────────
export function LoadingBox({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-text-muted">
      <Spinner /> <span className="text-sm">{label}</span>
    </div>
  );
}

// ── ErrorBox ──────────────────────────────────────────────────────────────
export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-accent-danger/5 border border-accent-danger/20 rounded-lg p-4">
      <p className="text-sm text-accent-danger">{message}</p>
    </div>
  );
}

// ── TickerPills ───────────────────────────────────────────────────────────
export function TickerPills({
  tickers, active, onSelect, multi = false,
}: {
  tickers: string[];
  active: string | string[];
  onSelect: (t: string) => void;
  multi?: boolean;
}) {
  const isActive = (t: string) =>
    Array.isArray(active) ? active.includes(t) : active === t;

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {tickers.map((t) => (
        <button
          key={t}
          onClick={() => onSelect(t)}
          className={clsx(
            'px-3 py-1.5 rounded-md text-xs font-medium border transition-colors',
            isActive(t)
              ? 'bg-accent-primary text-white border-accent-primary'
              : 'bg-surface border-border text-text-muted hover:bg-surface-hover',
          )}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

// ── Table ─────────────────────────────────────────────────────────────────
export function Table({
  headers, rows,
}: {
  headers: string[];
  rows: (string | ReactNode)[][];
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-surface border-b border-border">
            {headers.map((h) => (
              <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0 hover:bg-surface/50">
              {row.map((cell, j) => (
                <td key={j} className="py-2 px-3 text-xs text-text-secondary">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
