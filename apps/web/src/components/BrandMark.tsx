export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand" aria-label="Compound Zero">
      <div className="brand-mark" aria-hidden="true">
        <span className="brand-mark__arc brand-mark__arc--one" />
        <span className="brand-mark__arc brand-mark__arc--two" />
        <span className="brand-mark__zero">0</span>
      </div>
      {!compact && (
        <div className="brand-copy">
          <span className="brand-copy__name">COMPOUND</span>
          <span className="brand-copy__zero">ZERO</span>
        </div>
      )}
    </div>
  );
}

