export interface ClampedElementSize {
  clientHeight: number;
  scrollHeight: number;
}

/** Return whether clamped content has more rendered height than is visible. */
export function hasClampedOverflow({
  clientHeight,
  scrollHeight,
}: ClampedElementSize): boolean {
  return scrollHeight > clientHeight + 1;
}
