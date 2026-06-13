import { Wind, Droplets, Eye, Gauge } from 'lucide-react';
import type { WeatherSnapshot } from '../types';
import { formatTemp, formatWind, temperatureClass, weatherIconUrl } from '../utils/formatters';

interface Props {
  weather: WeatherSnapshot;
}

export function WeatherCard({ weather }: Props) {
  const { current } = weather;

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            {weather.city}
            <span className="text-base text-gray-500 ml-2 font-normal">
              {weather.country_code}
            </span>
          </h2>
          <p className="text-gray-600 capitalize mt-1">{current.description}</p>
        </div>
        <img
          src={weatherIconUrl(current.icon_code)}
          alt={current.description}
          className="w-20 h-20 -mt-2"
        />
      </div>

      <div className="flex items-baseline gap-4 mb-6">
        <div className={`text-6xl font-light ${temperatureClass(current.temperature_c)}`}>
          {formatTemp(current.temperature_c)}
        </div>
        <div className="text-gray-500">
          feels like {formatTemp(current.feels_like_c)}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric icon={<Droplets className="w-4 h-4" />} label="Humidity" value={`${current.humidity_pct}%`} />
        <Metric icon={<Wind className="w-4 h-4" />} label="Wind" value={formatWind(current.wind_speed_mps)} />
        <Metric icon={<Gauge className="w-4 h-4" />} label="Pressure" value={`${current.pressure_hpa} hPa`} />
        {current.visibility_m != null && (
          <Metric
            icon={<Eye className="w-4 h-4" />}
            label="Visibility"
            value={`${(current.visibility_m / 1000).toFixed(1)} km`}
          />
        )}
      </div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-0.5">
        {icon}
        {label}
      </div>
      <div className="text-sm font-medium text-gray-900">{value}</div>
    </div>
  );
}
