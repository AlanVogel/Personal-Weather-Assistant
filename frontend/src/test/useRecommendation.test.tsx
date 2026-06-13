import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRecommendation } from '../hooks/useRecommendation';
import { api } from '../services/api';
import type { WeatherWithRecommendation } from '../types';

vi.mock('../services/api', () => ({
  api: {
    getRecommendation: vi.fn(),
    askFollowUp: vi.fn(),
  },
}));

const mockApi = api as unknown as {
  getRecommendation: ReturnType<typeof vi.fn>;
  askFollowUp: ReturnType<typeof vi.fn>;
};

const fakeData = {
  target_date: '2026-06-13',
  weather: { city: 'Zagreb', country_code: 'HR', current: {}, forecast: [] },
  recommendation: { summary: 'Mild day', clothing: { items: [] }, activities: { suggested: [] } },
} as unknown as WeatherWithRecommendation;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useRecommendation', () => {
  it('starts idle', () => {
    const { result } = renderHook(() => useRecommendation());
    expect(result.current.status).toBe('idle');
    expect(result.current.data).toBeNull();
  });

  it('transitions to success and stores data', async () => {
    mockApi.getRecommendation.mockResolvedValue(fakeData);
    const { result } = renderHook(() => useRecommendation());

    await act(async () => {
      await result.current.fetchRecommendation('Zagreb');
    });

    expect(result.current.status).toBe('success');
    expect(result.current.data?.weather.city).toBe('Zagreb');
    expect(mockApi.getRecommendation).toHaveBeenCalledWith('Zagreb', undefined);
  });

  it('surfaces an error message on failure', async () => {
    mockApi.getRecommendation.mockRejectedValue(new Error('City not found'));
    const { result } = renderHook(() => useRecommendation());

    await act(async () => {
      await result.current.fetchRecommendation('Nowhere');
    });

    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe('City not found');
  });

  it('appends follow-up answers in order', async () => {
    mockApi.getRecommendation.mockResolvedValue(fakeData);
    mockApi.askFollowUp.mockResolvedValue({ answer: 'Yes, great for cycling.' });
    const { result } = renderHook(() => useRecommendation());

    await act(async () => {
      await result.current.fetchRecommendation('Zagreb');
    });
    await act(async () => {
      await result.current.askFollowUp('Can I cycle?');
    });

    await waitFor(() => expect(result.current.followUps).toHaveLength(1));
    expect(result.current.followUps[0]).toEqual({
      question: 'Can I cycle?',
      answer: 'Yes, great for cycling.',
    });
  });
});
