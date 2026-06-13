export function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse-slow">
      <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8">
        <div className="flex items-start justify-between mb-6">
          <div className="space-y-2">
            <div className="h-7 w-32 bg-gray-200 rounded" />
            <div className="h-4 w-40 bg-gray-200 rounded" />
          </div>
          <div className="w-20 h-20 bg-gray-200 rounded-full" />
        </div>
        <div className="h-16 w-32 bg-gray-200 rounded mb-6" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-gray-100 rounded-lg h-16" />
          ))}
        </div>
      </div>
      <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8 space-y-4">
        <div className="h-6 w-40 bg-gray-200 rounded" />
        <div className="space-y-2">
          <div className="h-4 w-full bg-gray-200 rounded" />
          <div className="h-4 w-5/6 bg-gray-200 rounded" />
          <div className="h-4 w-3/4 bg-gray-200 rounded" />
        </div>
      </div>
    </div>
  );
}
