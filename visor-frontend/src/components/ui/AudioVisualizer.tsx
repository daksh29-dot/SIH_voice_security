import React, { useEffect, useRef } from 'react';
import { audioService } from '@/services/audioService';

interface AudioVisualizerProps {
  state: 'IDLE' | 'RECORDING' | 'ANALYZING' | 'ERROR';
  height?: number;
}

export function AudioVisualizer({ state, height = 120 }: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let time = 0;
    
    // Ribbon Configuration: Colors matching the visual design tokens
    const ribbons = [
      { color: 'rgba(139, 61, 255, 0.9)', speed: 0.02, freq: 0.015, ampPhase: 0, lineWidth: 3 },       // Violet
      { color: 'rgba(217, 163, 255, 0.6)', speed: 0.015, freq: 0.018, ampPhase: 1, lineWidth: 2 },      // Lavender
      { color: 'rgba(213, 255, 69, 0.8)', speed: 0.025, freq: 0.01, ampPhase: 2, lineWidth: 1.5 },      // Electric-lime
      { color: 'rgba(255, 100, 255, 0.5)', speed: 0.01, freq: 0.022, ampPhase: 3, lineWidth: 1.5 },     // Magenta
      { color: 'rgba(0, 255, 255, 0.4)', speed: 0.018, freq: 0.014, ampPhase: 4, lineWidth: 1 },        // Cyan
    ];

    let smoothedAudioAmplitude = 0;
    const freqData = new Uint8Array(256);

    let isPageVisible = !document.hidden;
    const handleVisibilityChange = () => {
      isPageVisible = !document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const render = () => {
      animationId = requestAnimationFrame(render);
      if (!isPageVisible) return; // Pause rendering if tab is hidden

      const width = canvas.width;
      const height = canvas.height;

      // Ensure crisp rendering on high-DPI displays
      const dpr = window.devicePixelRatio || 1;
      const displayWidth = Math.floor(canvas.clientWidth * dpr);
      const displayHeight = Math.floor(canvas.clientHeight * dpr);
      
      if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
      }

      // Clear with slight trailing effect for smooth bloom/motion blur
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(13, 4, 28, 0.3)'; // Match #0D041C background with transparency
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      let targetAmp = 0.05; // Base idle breathing amplitude
      
      if (state === 'RECORDING') {
        const analyser = audioService.getAnalyser();
        if (analyser) {
          analyser.getByteFrequencyData(freqData);
          
          let sum = 0;
          for (let i = 0; i < analyser.frequencyBinCount; i++) {
            sum += freqData[i];
          }
          const avg = sum / analyser.frequencyBinCount;
          
          // Soft noise floor: subtract threshold
          const normalized = Math.max(0, (avg - 5) / 150);
          
          // Bounded visual gain
          targetAmp = 0.05 + Math.min(normalized, 1.2);
        } else {
          // Waiting for permissions or analyser initialization
          targetAmp = 0.05 + Math.sin(time * 0.05) * 0.02;
        }
      } else if (state === 'ANALYZING') {
        // Visually distinct flowing loop for processing
        targetAmp = 0.2 + Math.sin(time * 0.08) * 0.05;
      } else if (state === 'ERROR') {
        targetAmp = 0;
      }

      if (prefersReducedMotion) {
        // If reduced motion is requested, just render a restrained bar
        ctx.fillStyle = ribbons[0].color;
        const barHeight = Math.min(canvas.height, (targetAmp / 1.5) * canvas.height);
        ctx.fillRect(0, canvas.height - barHeight, canvas.width, barHeight);
        return;
      }

      // Fast attack, slow release (exponential smoothing)
      if (targetAmp > smoothedAudioAmplitude) {
        smoothedAudioAmplitude += (targetAmp - smoothedAudioAmplitude) * 0.4; // Fast attack
      } else {
        smoothedAudioAmplitude += (targetAmp - smoothedAudioAmplitude) * 0.05; // Slow release
      }

      // Prevent division by zero or negative amplitudes
      smoothedAudioAmplitude = Math.max(0, smoothedAudioAmplitude);

      time += 1;

      // Draw ribbons
      ctx.globalCompositeOperation = 'lighter';
      ctx.scale(dpr, dpr);
      
      const midY = canvas.clientHeight / 2;

      ribbons.forEach((ribbon, i) => {
        ctx.beginPath();
        const startX = -50;
        const endX = canvas.clientWidth + 50;

        for (let x = startX; x <= endX; x += 4) {
          // Hanning-style envelope to taper ends smoothly to 0
          const envelope = Math.sin((x / canvas.clientWidth) * Math.PI);
          
          // Ribbon-specific secondary animation
          const ribbonAmpVariation = Math.sin(time * 0.015 + ribbon.ampPhase) * 0.3 + 1;
          
          const currentAmp = smoothedAudioAmplitude * ribbonAmpVariation * (canvas.clientHeight * 0.4) * envelope;
          
          const y = midY + Math.sin(x * ribbon.freq + time * ribbon.speed) * currentAmp;
          
          if (x === startX) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }

        ctx.strokeStyle = ribbon.color;
        ctx.lineWidth = ribbon.lineWidth;
        
        // Subtle glow
        ctx.shadowBlur = 10;
        ctx.shadowColor = ribbon.color;
        
        ctx.stroke();
      });
      
      ctx.scale(1/dpr, 1/dpr);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [state]);

  return (
    <div style={{ height, width: '100%', position: 'relative' }}>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block', borderRadius: '12px' }}
      />
    </div>
  );
}
