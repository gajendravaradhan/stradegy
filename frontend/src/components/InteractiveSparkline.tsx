import { useState, useRef, useCallback } from "react";

interface DataPoint {
  date: string;
  close: number;
}

export default function InteractiveSparkline({ data, height = 100 }: { data: DataPoint[]; height?: number }) {
  if (!data || data.length < 2) return null;

  const prices = data.map((d) => d.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 300;

  const points = prices.map((price, i) => {
    const x = (i / (prices.length - 1)) * width;
    const y = height - ((price - min) / range) * (height - 20) - 10;
    return { x, y, price, date: data[i].date };
  });

  const isProfit = prices[prices.length - 1] >= prices[0];
  const strokeColor = isProfit ? "hsl(142 76% 45%)" : "hsl(0 72% 51%)";

  const areaPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.y}`)
    .join(" ")
    .concat(` L ${width},${height} L 0,${height} Z`);

  const [hovered, setHovered] = useState<{ index: number; x: number; y: number; price: number; date: string } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const handleMove = useCallback((clientX: number) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const svgX = ((clientX - rect.left) / rect.width) * width;
    let closestIndex = 0;
    let closestDist = Infinity;
    points.forEach((p, i) => {
      const dist = Math.abs(p.x - svgX);
      if (dist < closestDist) {
        closestDist = dist;
        closestIndex = i;
      }
    });
    setHovered({
      index: closestIndex,
      x: points[closestIndex].x,
      y: points[closestIndex].y,
      price: points[closestIndex].price,
      date: points[closestIndex].date,
    });
  }, [points, width]);

  return (
    <div className="relative w-full">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ height }}
        preserveAspectRatio="none"
        onMouseMove={(e) => handleMove(e.clientX)}
        onMouseLeave={() => setHovered(null)}
        onTouchMove={(e) => {
          e.preventDefault();
          handleMove(e.touches[0].clientX);
        }}
        onTouchEnd={() => setHovered(null)}
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#areaGrad)" />
        <polyline fill="none" stroke={strokeColor} strokeWidth="2" points={points.map((p) => `${p.x},${p.y}`).join(" ")} strokeLinecap="round" strokeLinejoin="round" />

        {hovered && (
          <>
            <line x1={hovered.x} y1={0} x2={hovered.x} y2={height} stroke="white" strokeOpacity="0.2" strokeWidth="1" strokeDasharray="4 4" />
            <circle cx={hovered.x} cy={hovered.y} r="5" fill={strokeColor} stroke="white" strokeWidth="2" />
          </>
        )}
      </svg>

      {hovered && (
        <div
          className="absolute pointer-events-none z-10 px-2 py-1 rounded-lg bg-popover text-popover-foreground text-[11px] font-medium shadow-lg border border-border/40"
          style={{
            left: `${(hovered.x / width) * 100}%`,
            top: `${(hovered.y / height) * 100}%`,
            transform: "translate(-50%, -120%)",
          }}
        >
          <div className="font-mono-value">${hovered.price.toFixed(2)}</div>
          <div className="text-[10px] text-muted-foreground">{hovered.date}</div>
        </div>
      )}
    </div>
  );
}
