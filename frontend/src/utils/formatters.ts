import { addDays, format, isValid, parseISO } from 'date-fns';

export function formatDate(input: string | Date, pattern = 'EEE, MMM d'): string {
  const date = typeof input === 'string' ? parseISO(input) : input;
  if (!isValid(date)) return '';
  return format(date, pattern);
}

export function todayIso(): string {
  return format(new Date(), 'yyyy-MM-dd');
}

export function maxForecastIso(): string {
  return format(addDays(new Date(), 5), 'yyyy-MM-dd');
}

export function formatTemp(c: number): string {
  return `${Math.round(c)}°C`;
}

export function formatWind(mps: number): string {
  return `${mps.toFixed(1)} m/s`;
}

export function temperatureClass(c: number): string {
  if (c >= 28) return 'text-weather-warm';
  if (c >= 18) return 'text-weather-mild';
  if (c >= 8) return 'text-weather-cool';
  return 'text-weather-cold';
}

export function weatherIconUrl(iconCode: string): string {
  return `https://openweathermap.org/img/wn/${iconCode}@2x.png`;
}
