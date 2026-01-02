import { useRef, useEffect, useState } from 'react';

interface HLSPlayerProps {
  src: string;
  autoPlay?: boolean;
  muted?: boolean;
}

export default function HLSPlayer({ src, autoPlay = true, muted = true }: HLSPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    // Dynamically import hls.js
    import('hls.js').then(({ default: Hls }) => {
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 90
        });
        
        hls.loadSource(src);
        hls.attachMedia(video);
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          setIsLoading(false);
          if (autoPlay) {
            video.play().catch(() => {
              // Autoplay blocked, user needs to interact
            });
          }
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            setError('Failed to load video stream');
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                // Try to recover
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                hls.destroy();
                break;
            }
          }
        });

        return () => {
          hls.destroy();
        };
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        video.src = src;
        setIsLoading(false);
        if (autoPlay) {
          video.play().catch(() => {});
        }
      } else {
        setError('HLS not supported in this browser');
      }
    }).catch(() => {
      setError('Failed to load HLS player');
    });
  }, [src, autoPlay]);

  if (error) {
    return (
      <div style={{ 
        backgroundColor: '#374151', 
        borderRadius: '0.5rem', 
        padding: '1rem', 
        textAlign: 'center',
        color: '#F87171'
      }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', borderRadius: '0.5rem', overflow: 'hidden', backgroundColor: 'black' }}>
      {isLoading && (
        <div style={{ 
          position: 'absolute', 
          inset: 0, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          backgroundColor: 'rgba(0,0,0,0.7)'
        }}>
          Loading preview...
        </div>
      )}
      <video
        ref={videoRef}
        style={{ width: '100%', aspectRatio: '16/9' }}
        controls
        muted={muted}
        playsInline
      />
      <div style={{ 
        position: 'absolute', 
        top: '0.5rem', 
        right: '0.5rem', 
        padding: '0.25rem 0.5rem', 
        backgroundColor: '#DC2626',
        color: 'white',
        fontSize: '0.75rem',
        fontWeight: 'bold',
        borderRadius: '0.25rem'
      }}>
        LIVE PREVIEW
      </div>
    </div>
  );
}
