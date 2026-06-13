import { useCallback, useState } from 'react';
import { api } from '../services/api';
import type { FollowUpAnswer, WeatherWithRecommendation } from '../types';

type Status = 'idle' | 'loading' | 'success' | 'error';

interface UseRecommendationState {
  status: Status;
  data: WeatherWithRecommendation | null;
  error: string | null;
  followUps: { question: string; answer: string }[];
  followUpLoading: boolean;
}

const initialState: UseRecommendationState = {
  status: 'idle',
  data: null,
  error: null,
  followUps: [],
  followUpLoading: false,
};

export function useRecommendation() {
  const [state, setState] = useState<UseRecommendationState>(initialState);

  const fetchRecommendation = useCallback(async (city: string, targetDate?: string) => {
    setState({ ...initialState, status: 'loading' });
    try {
      const data = await api.getRecommendation(city, targetDate);
      setState({
        status: 'success',
        data,
        error: null,
        followUps: [],
        followUpLoading: false,
      });
    } catch (error) {
      setState({
        status: 'error',
        data: null,
        error: error instanceof Error ? error.message : 'Unknown error',
        followUps: [],
        followUpLoading: false,
      });
    }
  }, []);

  const askFollowUp = useCallback(
    async (question: string) => {
      if (!state.data) return;

      setState((prev) => ({ ...prev, followUpLoading: true }));
      try {
        const result: FollowUpAnswer = await api.askFollowUp({
          city: state.data.weather.city,
          targetDate: state.data.target_date,
          previousRecommendation: state.data.recommendation,
          question,
        });
        setState((prev) => ({
          ...prev,
          followUpLoading: false,
          followUps: [...prev.followUps, { question, answer: result.answer }],
        }));
      } catch (error) {
        setState((prev) => ({
          ...prev,
          followUpLoading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    },
    [state.data],
  );

  const reset = useCallback(() => setState(initialState), []);

  return {
    ...state,
    fetchRecommendation,
    askFollowUp,
    reset,
  };
}
