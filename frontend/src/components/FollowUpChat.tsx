import { FormEvent, useState } from 'react';
import { Send, MessageCircle, User, Bot } from 'lucide-react';

interface Props {
  onAsk: (question: string) => void;
  isLoading: boolean;
  history: { question: string; answer: string }[];
}

const SUGGESTED_QUESTIONS = [
  'What about going for a run?',
  'Is this a good day to wash my car?',
  'Should I take an umbrella?',
];

export function FollowUpChat({ onAsk, isLoading, history }: Props) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3) return;
    onAsk(trimmed);
    setQuestion('');
  };

  const handleSuggested = (suggested: string) => {
    onAsk(suggested);
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-1 flex items-center gap-2">
        <MessageCircle className="w-5 h-5 text-indigo-500" />
        Ask a follow-up
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Get answers tailored to today's weather and previous suggestions.
      </p>

      {history.length > 0 && (
        <div className="space-y-3 mb-4 max-h-80 overflow-y-auto">
          {history.map((entry, index) => (
            <div key={index} className="space-y-2">
              <div className="flex gap-2">
                <User className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-800">
                  {entry.question}
                </div>
              </div>
              <div className="flex gap-2">
                <Bot className="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" />
                <div className="bg-indigo-50 rounded-lg px-3 py-2 text-sm text-gray-800 whitespace-pre-wrap">
                  {entry.answer}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything about today's weather..."
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          disabled={isLoading}
          maxLength={500}
        />
        <button
          type="submit"
          disabled={isLoading || question.trim().length < 3}
          className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
        >
          <Send className="w-4 h-4" />
          {isLoading ? 'Thinking…' : 'Ask'}
        </button>
      </form>

      {history.length === 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-2">Suggestions:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => handleSuggested(suggestion)}
                disabled={isLoading}
                className="px-3 py-1 text-sm bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 disabled:opacity-50 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
