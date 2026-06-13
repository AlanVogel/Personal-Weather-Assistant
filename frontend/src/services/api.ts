import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  ApiError,
  DailyRecommendation,
  FollowUpAnswer,
  WeatherWithRecommendation,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Normalize FastAPI's `detail` field into a single message.
 * Domain errors send a string; 422 validation errors send an array of
 * { loc, msg, type } objects. Returns null when there's nothing usable.
 */
export function parseApiErrorDetail(detail: ApiError['detail']): string | null {
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  const messages = detail.map((item) => item.msg).filter(Boolean);
  return messages.length > 0 ? messages.join('; ') : null;
}

class ApiClient {
  private readonly client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 60_000,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  async getRecommendation(
    city: string,
    targetDate?: string,
  ): Promise<WeatherWithRecommendation> {
    return this.post<WeatherWithRecommendation>('/api/recommendations', {
      city,
      target_date: targetDate ?? null,
    });
  }

  async askFollowUp(params: {
    city: string;
    targetDate: string;
    previousRecommendation: DailyRecommendation;
    question: string;
  }): Promise<FollowUpAnswer> {
    return this.post<FollowUpAnswer>('/api/recommendations/followup', {
      city: params.city,
      target_date: params.targetDate,
      previous_recommendation: params.previousRecommendation,
      user_question: params.question,
    });
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    try {
      const { data } = await this.client.post<T>(path, body);
      return data;
    } catch (error) {
      throw this.translateError(error);
    }
  }

  private translateError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      const message = parseApiErrorDetail(axiosError.response?.data?.detail);
      if (message) {
        return new Error(message);
      }
      if (axiosError.code === 'ECONNABORTED') {
        return new Error('Request timed out. Please try again.');
      }
      if (!axiosError.response) {
        return new Error('Could not reach the server. Is it running?');
      }
      return new Error(`Server error (${axiosError.response.status})`);
    }
    return error instanceof Error ? error : new Error('Unknown error');
  }
}

export const api = new ApiClient();
