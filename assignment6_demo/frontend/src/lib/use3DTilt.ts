import { useRef, useCallback, type MouseEvent } from 'react';

interface TiltOptions {
  maxTilt?: number;
  scale?: number;
  perspective?: number;
  speed?: number;
  glare?: boolean;
}

export function use3DTilt<T extends HTMLElement = HTMLDivElement>(options: TiltOptions = {}) {
  const {
    maxTilt = 8,
    scale = 1.025,
    perspective = 800,
    speed = 300,
  } = options;

  const ref = useRef<T>(null);

  const onMouseMove = useCallback((e: MouseEvent<T>) => {
    const el = ref.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = -((y - centerY) / centerY) * maxTilt;
    const rotateY = ((x - centerX) / centerX) * maxTilt;

    const glareX = (x / rect.width) * 100;
    const glareY = (y / rect.height) * 100;

    el.style.transform = `perspective(${perspective}px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(${scale}, ${scale}, ${scale})`;
    el.style.transition = 'transform 80ms ease-out';
    el.style.setProperty('--glare-x', `${glareX.toFixed(1)}%`);
    el.style.setProperty('--glare-y', `${glareY.toFixed(1)}%`);
    el.style.setProperty('--glare-opacity', '0.25');
  }, [maxTilt, scale, perspective]);

  const onMouseLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;

    el.style.transform = `perspective(${perspective}px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
    el.style.transition = `transform ${speed}ms cubic-bezier(0.2, 0.8, 0.2, 1)`;
    el.style.setProperty('--glare-opacity', '0');
  }, [perspective, speed]);

  return { ref, onMouseMove, onMouseLeave };
}
