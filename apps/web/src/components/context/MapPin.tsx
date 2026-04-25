import type { MapPinBlock } from '@/lib/types/blocks';

export function MapPin({ name, address, walk_minutes, distance_m }: MapPinBlock) {
  return (
    <div className="map-pin">
      <div className="map-pin__pin" aria-hidden>📍</div>
      <div className="map-pin__body">
        <div className="map-pin__name">{name}</div>
        {address && <div className="map-pin__address">{address}</div>}
        {(typeof walk_minutes === 'number' || typeof distance_m === 'number') && (
          <div className="map-pin__meta">
            {typeof walk_minutes === 'number' && <span>🚶 {walk_minutes}분</span>}
            {typeof distance_m === 'number' && <span>{distance_m}m</span>}
          </div>
        )}
      </div>
    </div>
  );
}
