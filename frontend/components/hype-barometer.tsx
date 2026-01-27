"use client";

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";

interface ToolStats {
  githubStars: string;
  hnMentions: number;
  pypiDownloads: string;
  lastUpdated: string;
}

interface HypeBarometerProps {
  name: string;
  score: number;
  url: string;
  stats: ToolStats;
}

function getHeatColor(score: number): string {
  if (score >= 80) return "from-orange-500 to-red-600";
  if (score >= 60) return "from-amber-400 to-orange-500";
  if (score >= 40) return "from-yellow-300 to-amber-400";
  if (score >= 20) return "from-yellow-200 to-yellow-300";
  return "from-sky-100 to-sky-200";
}

function Flames({ intensity, id }: { intensity: number; id: string }) {
  if (intensity < 30) return null;
  
  const opacity = Math.min((intensity - 30) / 70, 1);
  const flameHeight = 12 + (intensity / 100) * 20;
  
  return (
    <div 
      className="absolute pointer-events-none overflow-visible"
      style={{ 
        opacity,
        top: `-${flameHeight}px`,
        bottom: `-${flameHeight * 0.5}px`,
        left: '-4px',
        right: '-4px'
      }}
    >
      <svg
        viewBox="0 0 100 50"
        className="w-full h-full"
        preserveAspectRatio="none"
      >
        <defs>
          {/* Outer red/dark orange - like the image edge */}
          <linearGradient id={`flameRed-${id}`} x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#c92a2a" />
            <stop offset="50%" stopColor="#e03131" />
            <stop offset="100%" stopColor="#ff6b6b" />
          </linearGradient>
          {/* Middle orange layer */}
          <linearGradient id={`flameOrange-${id}`} x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#e8590c" />
            <stop offset="50%" stopColor="#fd7e14" />
            <stop offset="100%" stopColor="#ffa94d" />
          </linearGradient>
          {/* Inner yellow/white hot core */}
          <linearGradient id={`flameYellow-${id}`} x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#f59f00" />
            <stop offset="40%" stopColor="#fcc419" />
            <stop offset="100%" stopColor="#fff3bf" />
          </linearGradient>
        </defs>
        
        {/* Outer red flames - smooth organic curves like the reference */}
        <path 
          d="M0,50 
             C2,45 3,38 2,30 C3,25 6,20 5,12 C7,18 10,22 12,28 C13,22 14,15 13,8 C16,15 19,22 20,30 
             C21,24 22,18 21,10 C24,18 27,26 28,34 C29,28 30,20 29,14 C32,22 35,30 36,38
             C37,32 38,24 37,16 C40,24 43,32 44,40 C45,34 46,26 45,18 C48,26 51,34 52,42
             C53,36 54,28 53,20 C56,28 59,36 60,44 C61,38 62,30 61,22 C64,30 67,38 68,46
             C69,40 70,32 69,24 C72,32 75,40 76,48 C77,42 78,34 77,26 C80,34 83,42 84,50
             C85,44 86,36 85,28 C88,36 91,44 92,50 C93,46 94,38 93,32 C96,40 99,46 100,50 Z"
          fill={`url(#flameRed-${id})`}
        />
        
        {/* Middle orange flames - slightly smaller */}
        <path 
          d="M5,50 
             C7,46 8,40 7,34 C9,30 11,25 10,18 C13,24 16,30 17,36 
             C18,30 19,24 18,16 C21,24 24,32 25,38 C26,32 27,26 26,20 C29,28 32,34 33,40
             C34,34 35,28 34,22 C37,30 40,36 41,42 C42,36 43,30 42,24 C45,32 48,38 49,44
             C50,38 51,32 50,26 C53,34 56,40 57,46 C58,40 59,34 58,28 C61,36 64,42 65,48
             C66,42 67,36 66,30 C69,38 72,44 73,50 C74,44 75,38 74,32 C77,40 80,46 81,50
             C82,46 83,40 82,34 C85,42 88,48 89,50 C90,46 91,42 90,38 C93,44 96,48 98,50 Z"
          fill={`url(#flameOrange-${id})`}
        />
        
        {/* Inner yellow flames - smallest, hottest core */}
        <path 
          d="M12,50 
             C14,46 15,42 14,36 C16,40 18,36 17,28 C20,34 23,40 24,44 
             C25,40 26,34 25,28 C28,36 31,42 32,46 C33,42 34,36 33,30 C36,38 39,44 40,48
             C41,44 42,38 41,32 C44,40 47,46 48,50 C49,46 50,40 49,34 C52,42 55,48 56,50
             C57,46 58,42 57,36 C60,44 63,48 64,50 C65,48 66,44 65,40 C68,46 71,50 72,50
             C73,48 74,44 73,40 C76,46 79,50 80,50 C81,48 82,46 81,42 C84,48 87,50 90,50 Z"
          fill={`url(#flameYellow-${id})`}
        />
      </svg>
    </div>
  );
}

export function HypeBarometer({ name, score, url, stats }: HypeBarometerProps) {
  const heatColor = getHeatColor(score);
  const flameIntensity = score >= 30 ? score : 0;

  return (
    <HoverCard openDelay={200} closeDelay={100}>
      <HoverCardTrigger asChild>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-4 py-4 border-b border-border last:border-b-0 hover:bg-secondary/30 transition-colors px-2 -mx-2 rounded cursor-pointer group"
        >
          <div className="w-32 shrink-0">
            <span className="font-medium text-foreground text-sm group-hover:underline">
              {name}
            </span>
          </div>

          <div className="flex-1 relative py-2">
            {/* Flame effect behind the bar */}
            <div 
              className="absolute inset-0 overflow-visible"
              style={{ width: `${score}%` }}
            >
              <Flames intensity={flameIntensity} id={name.replace(/\s/g, '-')} />
            </div>
            
            {/* The actual bar */}
            <div className="h-5 bg-secondary/80 rounded-full overflow-hidden relative z-10">
              <div
                className={`h-full bg-gradient-to-r ${heatColor} rounded-full transition-all duration-500`}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>

          <div className="w-10 shrink-0 text-right">
            <span className="text-lg font-semibold text-foreground tabular-nums">
              {score}
            </span>
          </div>
        </a>
      </HoverCardTrigger>
      <HoverCardContent className="w-64" side="top">
        <div className="space-y-2">
          <h4 className="font-semibold text-sm">{name}</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-muted-foreground">GitHub Stars</p>
              <p className="font-medium">{stats.githubStars}</p>
            </div>
            <div>
              <p className="text-muted-foreground">HN Mentions</p>
              <p className="font-medium">{stats.hnMentions}</p>
            </div>
            <div>
              <p className="text-muted-foreground">PyPI Downloads</p>
              <p className="font-medium">{stats.pypiDownloads}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Last Updated</p>
              <p className="font-medium">{stats.lastUpdated}</p>
            </div>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
