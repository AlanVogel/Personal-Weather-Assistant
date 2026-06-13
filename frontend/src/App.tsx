import { AlertCircle, Cloud } from 'lucide-react';
import { useRecommendation } from './hooks/useRecommendation';
import { WeatherForm } from './components/WeatherForm';
import { WeatherCard } from './components/WeatherCard';
import { RecommendationsCard } from './components/RecommendationsCard';
import { MultiDayForecast } from './components/MultiDayForecast';
import { FollowUpChat } from './components/FollowUpChat';
import { LoadingSkeleton } from './components/LoadingSkeleton';

function App() {
  const recommendation = useRecommendation();

  return (
    <div className="min-h-screen px-4 py-8 md:py-12">
      <div className="max-w-4xl mx-auto space-y-6">
        <header className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-2 mb-2">
            <Cloud className="w-8 h-8 text-blue-500" />
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900">
              Weather Assistant
            </h1>
          </div>
          <p className="text-gray-600">
            Real-time weather with personalized AI recommendations
          </p>
        </header>

        <WeatherForm
          onSubmit={recommendation.fetchRecommendation}
          isLoading={recommendation.status === 'loading'}
        />

        {recommendation.status === 'loading' && <LoadingSkeleton />}

        {recommendation.status === 'error' && recommendation.error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-red-900">Something went wrong</h3>
              <p className="text-sm text-red-700">{recommendation.error}</p>
            </div>
          </div>
        )}

        {recommendation.status === 'success' && recommendation.data && (
          <>
            <WeatherCard weather={recommendation.data.weather} />
            <RecommendationsCard recommendation={recommendation.data.recommendation} />
            <MultiDayForecast forecast={recommendation.data.weather.forecast} />
            <FollowUpChat
              onAsk={recommendation.askFollowUp}
              isLoading={recommendation.followUpLoading}
              history={recommendation.followUps}
            />
          </>
        )}

        <footer className="text-center text-xs text-gray-400 pt-8">
          Weather data from OpenWeatherMap · AI by Groq
        </footer>
      </div>
    </div>
  );
}

export default App;
