import type { ComparisonTableBlock } from '@/lib/types/blocks';

export function CompareTable({ candidates, axes }: ComparisonTableBlock) {
  const safeCandidates = candidates ?? [];
  const safeAxes = axes ?? [];
  return (
    <div className="compare">
      <table>
        <thead>
          <tr>
            <th></th>
            {safeCandidates.map((c, i) => (
              <th key={i}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {safeAxes.map((axis, i) => (
            <tr key={i}>
              <th>{axis.label}</th>
              {(axis.values ?? []).map((v, j) => (
                <td key={j} className={axis.best === j ? 'best' : ''}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
