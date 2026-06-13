import { describe, expect, it } from 'vitest';
import { parseApiErrorDetail } from '../services/api';

describe('parseApiErrorDetail', () => {
  it('returns a string detail unchanged (domain errors)', () => {
    expect(parseApiErrorDetail('City not found')).toBe('City not found');
  });

  it('joins messages from a 422 validation-error array', () => {
    const detail = [
      { loc: ['body', 'city'], msg: 'String should have at least 1 character', type: 'string_too_short' },
      { loc: ['body', 'target_date'], msg: 'Input should be a valid date', type: 'date_parsing' },
    ];
    expect(parseApiErrorDetail(detail)).toBe(
      'String should have at least 1 character; Input should be a valid date',
    );
  });

  it('returns null for undefined detail', () => {
    expect(parseApiErrorDetail(undefined)).toBeNull();
  });

  it('returns null for an empty array', () => {
    expect(parseApiErrorDetail([])).toBeNull();
  });
});
