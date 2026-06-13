import { describe, it, expect } from 'vitest';
import {
  formatTemp,
  formatWind,
  temperatureClass,
  weatherIconUrl,
  formatDate,
} from '../utils/formatters';

describe('formatTemp', () => {
  it('rounds and adds Celsius symbol', () => {
    expect(formatTemp(18.5)).toBe('19°C');
    expect(formatTemp(0)).toBe('0°C');
    expect(formatTemp(-5.2)).toBe('-5°C');
  });
});

describe('formatWind', () => {
  it('shows one decimal place with units', () => {
    expect(formatWind(3.2)).toBe('3.2 m/s');
    expect(formatWind(0)).toBe('0.0 m/s');
  });
});

describe('temperatureClass', () => {
  it('returns warm class for hot temperatures', () => {
    expect(temperatureClass(30)).toBe('text-weather-warm');
  });
  it('returns mild class for comfortable temperatures', () => {
    expect(temperatureClass(20)).toBe('text-weather-mild');
  });
  it('returns cool class for cool temperatures', () => {
    expect(temperatureClass(12)).toBe('text-weather-cool');
  });
  it('returns cold class for cold temperatures', () => {
    expect(temperatureClass(0)).toBe('text-weather-cold');
  });
});

describe('weatherIconUrl', () => {
  it('builds correct icon URL', () => {
    expect(weatherIconUrl('03d')).toBe('https://openweathermap.org/img/wn/03d@2x.png');
  });
});

describe('formatDate', () => {
  it('formats ISO date string', () => {
    const result = formatDate('2026-06-09');
    expect(result).toContain('Jun');
    expect(result).toContain('9');
  });

  it('returns empty string for invalid date', () => {
    expect(formatDate('not-a-date')).toBe('');
  });
});
