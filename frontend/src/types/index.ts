// Type definitions mirroring backend Pydantic models.
// Kept in sync manually — for production at scale, generate from OpenAPI schema.

export interface CurrentConditions {
  temperature_c: number;
  feels_like_c: number;
  humidity_pct: number;
  pressure_hpa: number;
  wind_speed_mps: number;
  wind_direction_deg: number | null;
  cloudiness_pct: number;
  visibility_m: number | null;
  condition: string;
  description: string;
  icon_code: string;
  observed_at: string;
}

export interface ForecastDay {
  date: string;
  temp_min_c: number;
  temp_max_c: number;
  avg_humidity_pct: number;
  chance_of_rain_pct: number;
  dominant_condition: string;
  description: string;
  icon_code: string;
  wind_speed_mps_avg: number;
}

export interface WeatherSnapshot {
  city: string;
  country_code: string;
  latitude: number;
  longitude: number;
  timezone_offset_seconds: number;
  current: CurrentConditions;
  forecast: ForecastDay[];
}

export type Priority = 'high' | 'medium' | 'low';

export interface ClothingAdvice {
  items: string[];
  reasoning: string;
}

export interface ActivityAdvice {
  suggested: string[];
  avoid: string[];
  reasoning: string;
}

export interface HealthTip {
  tip: string;
  priority: Priority;
}

export interface DailyRecommendation {
  summary: string;
  clothing: ClothingAdvice;
  activities: ActivityAdvice;
  health_tips: HealthTip[];
  weekly_advice: string | null;
}

export interface WeatherWithRecommendation {
  target_date: string;
  weather: WeatherSnapshot;
  recommendation: DailyRecommendation;
}

export interface FollowUpAnswer {
  answer: string;
}

// FastAPI returns `detail` as a string for our domain errors, but as an array
// of validation objects for 422 (request schema) errors. Handle both shapes.
export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiError {
  error?: string;
  detail?: string | ValidationErrorItem[];
}
