import type { ForecastDay } from '../types';
import { formatDate, formatTemp, weatherIconUrl } from '../utils/formatters';

interface Props {
  forecast: ForecastDay[];
}

export function MultiDayForecast({ forecast }: Props) {
  if (forecast.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">5-day forecast</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {forecast.map((day) => (
          <div
            key={day.date}
            className="flex flex-col items-center bg-gradient-to-b from-blue-50 to-white rounded-xl p-3"
          >
            <div className="text-xs font-medium text-gray-600 mb-1">
              {formatDate(day.date)}
            </div>
            <img
              src={weatherIconUrl(day.icon_code)}
              alt={day.description}
              className="w-12 h-12 -my-1"
            />
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-base font-semibold text-gray-900">
                {formatTemp(day.temp_max_c)}
              </span>
              <span className="text-xs text-gray-500">{formatTemp(day.temp_min_c)}</span>
            </div>
            <div className="text-xs text-gray-500 capitalize mt-1 text-center line-clamp-1">
              {day.description}
            </div>
            {day.chance_of_rain_pct > 20 && (
              <div className="text-xs text-blue-600 mt-1">
                💧 {day.chance_of_rain_pct}%
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
