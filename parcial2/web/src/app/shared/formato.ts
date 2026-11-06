const Z_ISO = /Z$|[+-]\d{2}:?\d{2}$/;

export function moneda(valor: unknown): string {
  const n = Number(valor);
  if (!Number.isFinite(n)) return '0,00';
  return n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function porcentaje(valor: unknown): string {
  const n = Number(valor);
  if (!Number.isFinite(n)) return '0%';
  return `${n.toLocaleString('es-BO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}%`;
}

export function fechaLocal(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(Z_ISO.test(iso) ? iso : `${iso}Z`);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function fechaCortaLocal(iso: string | null | undefined, conAnio = false): string {
  if (!iso) return '—';
  const d = new Date(Z_ISO.test(iso) ? iso : `${iso}Z`);
  if (isNaN(d.getTime())) return '—';
  const opts: Intl.DateTimeFormatOptions = { day: '2-digit', month: '2-digit' };
  if (conAnio) opts.year = 'numeric';
  return d.toLocaleDateString('es-BO', opts);
}
