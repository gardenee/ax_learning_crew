import type { MapPinBlock } from '@/lib/types/blocks';

export function MapPin({ name, address, walk_minutes, distance_m }: MapPinBlock) {
  return (
    <div className="map-pin">
      <div className="map-pin__pin" aria-hidden>📍</div>
      <div className="map-pin__body">
        <div className="map-pin__name">{name}</div>
        {address && <div className="map-pin__address">{address}</div>}
        {(walk_minutes !== undefined || distance_m !== undefined) && (
          <div className="map-pin__meta">
            {walk_minutes !== undefined && <span>🚶 {walk_minutes}분</span>}
            {distance_m !== undefined && <span>{distance_m}m</span>}
          </div>
        )}
      </div>
    </div>
  );
}
