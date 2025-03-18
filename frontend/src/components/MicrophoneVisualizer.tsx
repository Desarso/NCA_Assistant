import { useEffect, useRef } from "react";

interface Props {
  isListening: boolean;
  onClose: () => void;
  onMute: () => void;
}

const MicrophoneVisualizer = ({ isListening, onClose, onMute }: Props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number>(0);
  const mediaStreamRef = useRef<MediaStream | null>(null);


  useEffect(() => {
    if (isListening) {
      startVisualization();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  const startVisualization = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;

      animate();
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const animate = () => {
    if (!canvasRef.current || !analyserRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);

    const draw = () => {
      if (!isListening) return;

      analyserRef.current!.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Calculate average volume with more weight on lower frequencies
      const average =
        dataArray.reduce((a, b, i) => {
          // Give more weight to lower frequencies
          const weight = 1 - (i / dataArray.length) * 0.5;
          return a + b * weight;
        }, 0) / dataArray.length;

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const minRadius = 60;
      const maxRadius = 140;
      // Make radius more responsive with exponential scaling
      const radius =
        minRadius + Math.pow(average / 256, 1.5) * (maxRadius - minRadius);

      // Add glow effect
      ctx.shadowBlur = 15;
      ctx.shadowColor = "#818CF8";

      // Draw multiple circles for layered effect
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius - i * 5, 0, 2 * Math.PI);
        ctx.strokeStyle = `rgba(129, 140, 248, ${1 - i * 0.2})`;
        ctx.lineWidth = 3 - i;
        ctx.stroke();
      }

      // Dynamic fill with pulse effect
      const pulseIntensity = Math.sin(Date.now() * 0.005) * 0.2 + 0.8;
      ctx.fillStyle = `rgba(165, 180, 252, ${
        (average / 512) * pulseIntensity
      })`;
      ctx.fill();

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    draw();
  };

  return (
    <div className="flex flex-col items-center justify-center w-full h-full relative">
      <canvas
        ref={canvasRef}
        width="300"
        height="300"
        className="max-w-full max-h-full"
      />

      <div className="flex gap-8 mt-8">
        <button
          onClick={onClose}
          className="p-6 rounded-full bg-gray-800 hover:bg-gray-700 transition-colors"
          aria-label="Stop recording"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-8 w-8 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        <button
          onClick={onMute}
          className={`p-6 rounded-full transition-colors ${
            isListening
              ? "bg-gray-800 hover:bg-gray-700"
              : "bg-red-800 hover:bg-red-700"
          }`}
          aria-label={isListening ? "Mute microphone" : "Unmute microphone"}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-8 w-8 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
            {!isListening && (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 3l18 18"
              />
            )}
          </svg>
        </button>
      </div>
    </div>
  );
};

export default MicrophoneVisualizer;
