export function getAccountName(account: { name: string; display_name?: string | null }): string {
  return account.display_name ?? account.name
}

/**
 * Return a presentation-only copy ordered by the name users see.
 * The input is never mutated, which keeps React Query's cached account list intact.
 */
export function sortAccountsByDisplayName<
  T extends { name: string; display_name?: string | null },
>(accounts: readonly T[]): T[] {
  return [...accounts].sort((left, right) =>
    getAccountName(left).localeCompare(getAccountName(right), undefined, {
      numeric: true,
      sensitivity: 'base',
    }),
  )
}

/**
 * The bank's identifier for an account, masked to its last 4 chars, e.g. "•••• 1234".
 *
 * Banks commonly report every account under the same label (often the holder's
 * name), so this is what tells two of them apart. Null when the provider gave us
 * no identifier, so callers render nothing rather than an empty mask. Locale-neutral
 * by construction: dots and the bank's own digits, nothing to translate.
 */
export function formatAccountMask(account: { masked_number?: string | null }): string | null {
  return account.masked_number ? `•••• ${account.masked_number}` : null
}

/**
 * Account name with its mask appended, e.g. "Checking •••• 1234", for compact
 * single-line surfaces such as the account <select> options, where there is no
 * room for a secondary line. When the account has an explicit display_name, the
 * mask is omitted since the user-chosen label already distinguishes it.
 */
export function getAccountLabel(account: {
  name: string
  display_name?: string | null
  masked_number?: string | null
}): string {
  const name = getAccountName(account)
  // When the account has an explicit display_name the user set, it already
  // distinguishes this account from others so the mask suffix is redundant.
  if (account.display_name) return name
  const mask = formatAccountMask(account)
  return mask ? `${name} ${mask}` : name
}

/**
 * Borrower-facing loan title: strip KM/meta chips, rate/EMI/OS noise.
 * Numbers live in hero chips — title stays a short product name.
 */
export function clientLoanTitle(
  raw: string | null | undefined,
  fallback = 'Loan',
): string {
  if (!raw?.trim()) return fallback

  const parts = raw
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean)

  const kept: string[] = []
  for (const p of parts) {
    const low = p.toLowerCase()
    if (/^km:/.test(low) || /\bkm:/.test(low)) continue
    if (/do_not_flatten|no_flatten/.test(low)) continue
    if (/^foreclose/.test(low)) continue
    if (/^os[\s₹rs]/i.test(p)) continue
    if (/^tbpun/i.test(p.replace(/\s/g, ''))) continue
    kept.push(p)
  }

  // Name lives before an em-dash annotation (e.g. "— NO EMI …")
  let primary = (kept[0] || fallback).split(/\s*[—]\s*/)[0].trim()

  const tokens = primary.split(/\s*[·•]\s*/).map((x) => x.trim()).filter(Boolean)
  const clean: string[] = []
  for (const tok of tokens) {
    if (/^\d+(?:\.\d+)?%$/.test(tok)) break
    if (/^EMI\b/i.test(tok)) break
    if (/^tenor\b/i.test(tok)) break
    if (/^NO EMI\b/i.test(tok)) break
    if (/^half-yr/i.test(tok)) break
    if (/^O\/S\b/i.test(tok)) break
    if (/^prin\b/i.test(tok)) break
    if (/^OS\b/i.test(tok)) break
    if (/\([^)]*paid/i.test(tok)) break
    clean.push(tok)
  }

  let title = clean.join(' · ') || fallback

  const place = kept[1]
  if (
    place &&
    place.length <= 36 &&
    !/[;:=]/.test(place) &&
    !/km:|flatten|foreclose/i.test(place) &&
    !title.includes(place)
  ) {
    title = `${title} · ${place}`
  }

  return title || fallback
}

/** Format next due for hero chips; empty → em dash. */
export function formatLoanNextDue(
  nextDue: string | null | undefined,
  locale = 'en-IN',
): string {
  if (!nextDue) return '—'
  const d = new Date(`${nextDue}T00:00:00`)
  if (Number.isNaN(d.getTime())) return nextDue
  return d.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })
}
