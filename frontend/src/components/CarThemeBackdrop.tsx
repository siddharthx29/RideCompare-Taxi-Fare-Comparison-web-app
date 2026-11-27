import { useEffect, useRef, useState } from 'react';

interface CarThemeBackdropProps {
  darkMode: boolean;
}

interface LightStreak {
  lane: number;
  z: number;
  speed: number;
  isOncoming: boolean;
  width: number;
  prevX?: number;
  prevY?: number;
}

/**
 * Apple-style scroll-reactive car-themed background:
 * - Plays /car-bg.mp4 if placed in frontend/public/car-bg.mp4 with scroll-linked zoom, blur & speed boost.
 * - Renders a 60fps cinematic highway/city-drive canvas that shifts speed, perspective, color grading,
 *   and depth-of-field blur dynamically as the user scrolls.
 */
export function CarThemeBackdrop({ darkMode }: CarThemeBackdropProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const scrollProgressRef = useRef(0);
  const scrollBoostRef = useRef(0);
  const [videoReady, setVideoReady] = useState(false);
  const [scrollState, setScrollState] = useState({ progress: 0 });

  useEffect(() => {
    let lastY = window.scrollY;
    let rafUpdate = 0;

    const onScroll = () => {
      const currentY = window.scrollY;
      const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.min(1, Math.max(0, currentY / maxScroll));
      const delta = Math.abs(currentY - lastY);
      lastY = currentY;

      scrollProgressRef.current = progress;
      scrollBoostRef.current = Math.min(2.2, scrollBoostRef.current + delta * 0.015);

      if (videoRef.current && videoReady) {
        videoRef.current.playbackRate = Math.min(2.2, 1.0 + scrollBoostRef.current * 0.45);
      }

      if (!rafUpdate) {
        rafUpdate = window.requestAnimationFrame(() => {
          setScrollState({ progress });
          rafUpdate = 0;
        });
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      if (rafUpdate) window.cancelAnimationFrame(rafUpdate);
    };
  }, [videoReady]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId = 0;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const cars: LightStreak[] = Array.from({ length: 28 }, (_, idx) => ({
      lane: (idx % 4) - 1.5,
      z: (idx / 28) * 1.0 + 0.04,
      speed: 0.0038 + (idx % 5) * 0.001,
      isOncoming: idx % 2 === 0,
      width: 0.032 + (idx % 3) * 0.008,
    }));

    let dashOffset = 0;

    const render = () => {
      const progress = scrollProgressRef.current;
      const boost = scrollBoostRef.current;
      scrollBoostRef.current = Math.max(0, boost * 0.92);

      if (videoRef.current && videoReady && boost < 0.05) {
        videoRef.current.playbackRate = 1.0;
      }

      // Horizon shifts slightly with scroll for Apple-style parallax depth
      const horizonY = height * (0.47 - progress * 0.08);
      const vanishX = width * (0.5 + Math.sin(progress * Math.PI) * 0.04);

      // Dynamic sky color shifts from warm dusk -> deep midnight -> emerald/indigo night as you scroll
      const sky = ctx.createLinearGradient(0, 0, 0, horizonY);
      if (darkMode) {
        const r = Math.round(28 - progress * 14);
        const g = Math.round(22 + progress * 12);
        const b = Math.round(32 + progress * 24);
        sky.addColorStop(0, '#05070b');
        sky.addColorStop(0.6, '#0d121d');
        sky.addColorStop(1, `rgb(${r}, ${g}, ${b})`);
      } else {
        sky.addColorStop(0, '#dbe4f3');
        sky.addColorStop(0.65, '#eaeef6');
        sky.addColorStop(1, progress > 0.5 ? '#dfe9f5' : '#f4e4d9');
      }
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, width, horizonY);

      // Ambient city glow shifts hue with scroll
      const glow = ctx.createRadialGradient(vanishX, horizonY, 12, vanishX, horizonY, width * (0.46 + progress * 0.12));
      glow.addColorStop(
        0,
        progress < 0.5
          ? (darkMode ? 'rgba(255, 118, 56, 0.30)' : 'rgba(255, 118, 56, 0.20)')
          : (darkMode ? 'rgba(99, 130, 255, 0.28)' : 'rgba(99, 130, 255, 0.18)')
      );
      glow.addColorStop(0.55, darkMode ? 'rgba(16, 185, 129, 0.10)' : 'rgba(16, 185, 129, 0.07)');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      // City skyline silhouettes
      ctx.fillStyle = darkMode ? 'rgba(8, 11, 16, 0.92)' : 'rgba(130, 145, 170, 0.24)';
      const buildingCount = 28;
      const bWidth = width / buildingCount;
      for (let i = 0; i < buildingCount; i++) {
        const bHeight = ((Math.sin(i * 1.9 + progress * 0.8) + 1.25) * 32) + (i % 3) * 18;
        ctx.fillRect(i * bWidth, horizonY - bHeight, bWidth - 2, bHeight);
      }

      // Asphalt highway
      const roadGrad = ctx.createLinearGradient(0, horizonY, 0, height);
      if (darkMode) {
        roadGrad.addColorStop(0, '#0f131a');
        roadGrad.addColorStop(1, '#06080b');
      } else {
        roadGrad.addColorStop(0, '#cbd5e1');
        roadGrad.addColorStop(1, '#94a3b8');
      }
      ctx.fillStyle = roadGrad;
      ctx.fillRect(0, horizonY, width, height - horizonY);

      // Perspective lanes accelerating with scroll boost
      dashOffset = (dashOffset + 0.022 + boost * 0.028) % 1;
      for (const laneEdge of [-2.4, -1.2, 0, 1.2, 2.4]) {
        ctx.beginPath();
        const isCenter = laneEdge === 0;
        const isOuter = Math.abs(laneEdge) > 2;
        ctx.strokeStyle = isCenter
          ? 'rgba(255, 138, 80, 0.48)'
          : isOuter
            ? 'rgba(255, 255, 255, 0.24)'
            : 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = isOuter ? 2.4 : 1.5;

        if (!isOuter && !isCenter) {
          ctx.setLineDash([18, 22]);
          ctx.lineDashOffset = -dashOffset * 40;
        } else {
          ctx.setLineDash([]);
        }
        ctx.moveTo(vanishX + laneEdge * 18, horizonY);
        ctx.lineTo(vanishX + laneEdge * (width * 0.44), height);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Moving car light streaks with motion-blur trails
      const speedFactor = 1 + boost * 1.15;
      for (const car of cars) {
        car.z += (car.isOncoming ? car.speed : -car.speed * 0.8) * speedFactor;
        if (car.z > 1.05) {
          car.z = 0.03;
          car.prevX = undefined;
          car.prevY = undefined;
        }
        if (car.z < 0.03) {
          car.z = 1.02;
          car.prevX = undefined;
          car.prevY = undefined;
        }

        const perspective = Math.pow(car.z, 1.65);
        const y = horizonY + perspective * (height - horizonY);
        const spread = perspective * (width * 0.44) + 18;
        const x = vanishX + car.lane * (spread * 0.45);
        const lightHalfGap = (car.width * width * perspective) * 0.5 + 3;
        const radius = Math.max(1.8, 8 * perspective);

        const primaryColor = car.isOncoming
          ? 'rgba(255, 244, 220, 0.94)'
          : 'rgba(255, 92, 51, 0.94)';
        const haloColor = car.isOncoming
          ? 'rgba(170, 215, 255, 0.28)'
          : 'rgba(255, 80, 40, 0.34)';

        for (const offset of [-lightHalfGap, lightHalfGap]) {
          const lx = x + offset;
          if (car.prevX !== undefined && car.prevY !== undefined) {
            ctx.beginPath();
            ctx.strokeStyle = haloColor;
            ctx.lineWidth = Math.max(1.2, radius * 1.1);
            ctx.moveTo(car.prevX + offset, car.prevY);
            ctx.lineTo(lx, y);
            ctx.stroke();
          }

          const halo = ctx.createRadialGradient(lx, y, 0.5, lx, y, radius * 3.8);
          halo.addColorStop(0, primaryColor);
          halo.addColorStop(0.35, haloColor);
          halo.addColorStop(1, 'transparent');
          ctx.fillStyle = halo;
          ctx.beginPath();
          ctx.arc(lx, y, radius * 3.8, 0, Math.PI * 2);
          ctx.fill();
        }
        car.prevX = x;
        car.prevY = y;
      }

      animationId = window.requestAnimationFrame(render);
    };

    animationId = window.requestAnimationFrame(render);
    return () => {
      window.cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, [darkMode, videoReady]);

  const scale = 1 + scrollState.progress * 0.1;
  const blurPx = (scrollState.progress * 5).toFixed(1);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden select-none" aria-hidden="true">
      <div
        className="h-full w-full transition-transform duration-150 ease-out will-change-transform"
        style={{
          transform: `scale(${scale.toFixed(3)})`,
          filter: `blur(${blurPx}px)`,
        }}
      >
        <canvas ref={canvasRef} className="h-full w-full block" />
        <video
          ref={videoRef}
          src="/car-bg.mp4"
          autoPlay
          loop
          muted
          playsInline
          onCanPlay={() => setVideoReady(true)}
          onError={() => setVideoReady(false)}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${videoReady ? 'opacity-100' : 'opacity-0'}`}
        />
      </div>
      <div
        className={`absolute inset-0 transition-colors duration-300 ${
          darkMode
            ? 'bg-gradient-to-b from-black/50 via-black/38 to-black/68'
            : 'bg-gradient-to-b from-white/60 via-white/42 to-slate-100/72'
        }`}
      />
    </div>
  );
}
