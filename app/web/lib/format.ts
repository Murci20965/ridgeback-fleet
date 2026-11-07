// Dates in the API are local days, so they're parsed as UTC and shown as UTC. This stops a
// viewer's time zone from moving "2026-09-08" to the day before.

const parse = (iso: string) => new Date(`${iso}T00:00:00Z`);

const formatter = (options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...options });

const weekday = formatter({ weekday: "short" });
const day = formatter({ day: "numeric" });
const month = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short" });

export const shortWeekday = (iso: string) => weekday.format(parse(iso)).replace(",", "");
export const shortDate = (iso: string) => `${day.format(parse(iso))} ${month.format(parse(iso))}`;
export const fullDay = (iso: string) => `${shortWeekday(iso)} ${shortDate(iso)}`;

export function rangeLabel(from: string, to: string) {
  return from === to ? fullDay(from) : `${fullDay(from)} to ${fullDay(to)}`;
}

export function weekDays(start: string): string[] {
  return Array.from({ length: 7 }, (_, offset) => {
    const date = parse(start);
    date.setUTCDate(date.getUTCDate() + offset);
    return date.toISOString().slice(0, 10);
  });
}

const whole = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const formatCount = (value: number) => whole.format(value);
export const formatHours = (value: number) => oneDecimal.format(value);
