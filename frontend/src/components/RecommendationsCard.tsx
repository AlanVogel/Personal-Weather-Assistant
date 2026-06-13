import { Shirt, Activity, Heart, Lightbulb, AlertCircle } from 'lucide-react';
import type { DailyRecommendation, Priority } from '../types';

interface Props {
  recommendation: DailyRecommendation;
}

const PRIORITY_STYLES: Record<Priority, string> = {
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-gray-50 text-gray-600 border-gray-200',
};

export function RecommendationsCard({ recommendation }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8 space-y-6">
      <div className="border-l-4 border-blue-500 pl-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-blue-500" />
          Summary
        </h3>
        <p className="text-gray-700">{recommendation.summary}</p>
      </div>

      <Section
        icon={<Shirt className="w-5 h-5 text-purple-500" />}
        title="What to wear"
        reasoning={recommendation.clothing.reasoning}
      >
        <div className="flex flex-wrap gap-2">
          {recommendation.clothing.items.map((item) => (
            <span
              key={item}
              className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-full text-sm font-medium"
            >
              {item}
            </span>
          ))}
        </div>
      </Section>

      <Section
        icon={<Activity className="w-5 h-5 text-emerald-500" />}
        title="Activities"
        reasoning={recommendation.activities.reasoning}
      >
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-emerald-700 uppercase tracking-wide mb-1.5">
              Suggested
            </p>
            <div className="flex flex-wrap gap-2">
              {recommendation.activities.suggested.map((item) => (
                <span
                  key={item}
                  className="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full text-sm"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
          {recommendation.activities.avoid.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700 uppercase tracking-wide mb-1.5">
                Maybe skip
              </p>
              <div className="flex flex-wrap gap-2">
                {recommendation.activities.avoid.map((item) => (
                  <span
                    key={item}
                    className="px-3 py-1.5 bg-red-50 text-red-700 rounded-full text-sm"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </Section>

      {recommendation.health_tips.length > 0 && (
        <Section
          icon={<Heart className="w-5 h-5 text-pink-500" />}
          title="Health tips"
        >
          <div className="space-y-2">
            {recommendation.health_tips.map((tip, index) => (
              <div
                key={index}
                className={`flex items-start gap-2 px-3 py-2 rounded-lg border ${PRIORITY_STYLES[tip.priority]}`}
              >
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{tip.tip}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {recommendation.weekly_advice && (
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h4 className="text-sm font-semibold text-blue-900 mb-1">Looking ahead</h4>
          <p className="text-sm text-blue-800">{recommendation.weekly_advice}</p>
        </div>
      )}
    </div>
  );
}

function Section({
  icon,
  title,
  reasoning,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  reasoning?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      {reasoning && <p className="text-sm text-gray-600 mb-3 italic">{reasoning}</p>}
      {children}
    </div>
  );
}
