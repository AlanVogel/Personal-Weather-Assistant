import { FormEvent, useState } from 'react';
import { MapPin, Calendar, Sparkles } from 'lucide-react';
import { maxForecastIso, todayIso } from '../utils/formatters';

interface Props {
  onSubmit: (city: string, targetDate?: string) => void;
  isLoading: boolean;
}

const POPULAR_CITIES = ['Zagreb', 'Split', 'London', 'Paris', 'Tokyo', 'New York'];

export function WeatherForm({ onSubmit, isLoading }: Props) {
  const [city, setCity] = useState('');
  const [targetDate, setTargetDate] = useState(todayIso());

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = city.trim();
    if (!trimmed) return;
    onSubmit(trimmed, targetDate !== todayIso() ? targetDate : undefined);
  };

  const handleQuickCity = (quickCity: string) => {
    setCity(quickCity);
    onSubmit(quickCity, targetDate !== todayIso() ? targetDate : undefined);
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-1.5">
              <MapPin className="inline w-4 h-4 mr-1" />
              City
            </label>
            <input
              id="city"
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g., Zagreb, London"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
              maxLength={100}
              required
            />
          </div>
          <div>
            <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-1.5">
              <Calendar className="inline w-4 h-4 mr-1" />
              Date
            </label>
            <input
              id="date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              min={todayIso()}
              max={maxForecastIso()}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading || !city.trim()}
          className="w-full md:w-auto px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {isLoading ? 'Analyzing weather...' : 'Get recommendations'}
        </button>
      </form>

      <div className="mt-5 pt-5 border-t border-gray-100">
        <p className="text-xs text-gray-500 mb-2">Try a popular city:</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_CITIES.map((quickCity) => (
            <button
              key={quickCity}
              type="button"
              onClick={() => handleQuickCity(quickCity)}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              {quickCity}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
