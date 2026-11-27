import { useEffect, useRef, useState } from 'react';

interface AppleCarBackdropProps {
  darkMode: boolean;
}

/**
 * Scroll-reactive car video background using the uploaded /car-bg.mp4.
 * Changes scale, parallax, blur, color grade, and playback speed dynamically on scroll.
 */
export function AppleCarBackdrop({ darkMode }: AppleCarBackdropProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const scrollBoostRef = useRef(0);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const vid = videoRef.current;
    if (vid) {
      vid.play().catch(() => {});
    }
  }, []);

  useEffect(() => {
    let lastY = window.scrollY;
    let rafId = 0;
    let decayTimer = 0;

    const handleScroll = () => {
      const y = window.scrollY;
      const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.min(1, Math.max(0, y / maxScroll));
      const delta = Math.abs(y - lastY);
      lastY = y;

      scrollBoostRef.current = Math.min(1.0, scrollBoostRef.current + delta * 0.01);

      if (videoRef.current) {
        videoRef.current.playbackRate = Math.min(2.0, 1.0 + scrollBoostRef.current * 0.9);
      }

      window.clearTimeout(decayTimer);
      decayTimer = window.setTimeout(() => {
        scrollBoostRef.current = 0;
        if (videoRef.current) {
          videoRef.current.playbackRate = 1.0;
        }
      }, 180);

      if (!rafId) {
        rafId = window.requestAnimationFrame(() => {
          setScrollProgress(progress);
          rafId = 0;
        });
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.clearTimeout(decayTimer);
      if (rafId) window.cancelAnimationFrame(rafId);
    };
  }, []);

  const scale = 1 + scrollProgress * 0.22;
  const translateY = -(scrollProgress * 44);
  const rotateX = (scrollProgress * 3.5).toFixed(2);
  const blurPx = (scrollProgress * 9).toFixed(1);
  const hueDeg = Math.round(scrollProgress * 36);
  const saturate = (1.15 + scrollProgress * 0.45).toFixed(2);

  return (
    <>
      {/* Top scroll-progress indicator */}
      <div
        className="pointer-events-none fixed left-0 top-0 z-[60] h-[3px] bg-gradient-to-r from-[#ff7043] via-[#7c7bff] to-[#2ee59d] transition-all duration-100"
        style={{ width: `${Math.round(scrollProgress * 100)}%` }}
      />

      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden select-none" aria-hidden="true">
        <div
          className="h-full w-full transition-transform duration-150 ease-out will-change-transform"
          style={{
            transform: `perspective(1200px) rotateX(${rotateX}deg) translate3d(0, ${translateY.toFixed(1)}px, 0) scale(${scale.toFixed(3)})`,
            filter: `blur(${blurPx}px) saturate(${saturate}) hue-rotate(${hueDeg}deg)`,
          }}
        >
          <video
            ref={videoRef}
            src="/car-bg.mp4"
            autoPlay
            loop
            muted
            playsInline
            preload="auto"
            className={`h-full w-full object-cover ${darkMode ? 'opacity-65' : 'opacity-40'}`}
          />
        </div>

        {/* Scroll-Reactive Ambient Glow Orbs */}
        <div
          className="absolute -top-28 -left-24 h-[420px] w-[420px] rounded-full blur-3xl transition-all duration-300"
          style={{
            transform: `translate3d(${(scrollProgress * 140).toFixed(0)}px, ${(scrollProgress * 90).toFixed(0)}px, 0) scale(${(1 + scrollProgress * 0.3).toFixed(2)})`,
            background: scrollProgress < 0.5
              ? 'rgba(255, 107, 61, 0.22)'
              : 'rgba(124, 123, 255, 0.24)',
          }}
        />
        <div
          className="absolute bottom-[-110px] right-[-70px] h-[460px] w-[460px] rounded-full blur-3xl transition-all duration-300"
          style={{
            transform: `translate3d(${(-scrollProgress * 140).toFixed(0)}px, ${(-scrollProgress * 100).toFixed(0)}px, 0) scale(${(1.2 - scrollProgress * 0.22).toFixed(2)})`,
            background: scrollProgress < 0.5
              ? 'rgba(99, 102, 241, 0.18)'
              : 'rgba(46, 229, 157, 0.20)',
          }}
        />

        {/* Readability Scrim */}
        <div
          className="absolute inset-0 transition-colors duration-300"
          style={{
            background: darkMode
              ? `linear-gradient(180deg, rgba(9,11,14,${(0.38 + scrollProgress * 0.22).toFixed(2)}) 0%, rgba(11,14,20,${(0.32 + scrollProgress * 0.24).toFixed(2)}) 50%, rgba(7,9,12,${(0.58 + scrollProgress * 0.20).toFixed(2)}) 100%)`
              : `linear-gradient(180deg, rgba(242,245,250,${(0.58 + scrollProgress * 0.14).toFixed(2)}) 0%, rgba(238,242,247,${(0.48 + scrollProgress * 0.16).toFixed(2)}) 50%, rgba(226,232,240,${(0.68 + scrollProgress * 0.12).toFixed(2)}) 100%)`,
          }}
        />
      </div>
    </>
  );
}
