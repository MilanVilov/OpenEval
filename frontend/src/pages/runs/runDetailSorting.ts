export type GraderSortDirection = 'fail-first' | 'pass-first';

export interface GraderSort {
  graderName: string;
  direction: GraderSortDirection;
}

interface ResultWithComparerDetails {
  comparer_details: Record<string, unknown> | null;
}

function getGraderPassedValue(
  result: ResultWithComparerDetails,
  graderName: string,
): boolean | null {
  const detail = result.comparer_details?.[graderName];
  if (!detail || typeof detail !== 'object') {
    return null;
  }

  const passed = (detail as { passed?: unknown }).passed;
  return typeof passed === 'boolean' ? passed : null;
}

function getGraderSortRank(
  passed: boolean | null,
  direction: GraderSortDirection,
): number {
  if (passed == null) {
    return 2;
  }

  if (direction === 'fail-first') {
    return passed ? 1 : 0;
  }

  return passed ? 0 : 1;
}

export function getNextGraderSort(
  currentSort: GraderSort | null,
  graderName: string,
): GraderSort | null {
  if (!currentSort || currentSort.graderName !== graderName) {
    return { graderName, direction: 'fail-first' };
  }

  if (currentSort.direction === 'fail-first') {
    return { graderName, direction: 'pass-first' };
  }

  return null;
}

export function sortResultsByGrader<T extends ResultWithComparerDetails>(
  results: T[],
  sort: GraderSort | null,
): T[] {
  if (!sort) {
    return results;
  }

  return results
    .map((result, index) => ({ result, index }))
    .sort((left, right) => {
      const leftRank = getGraderSortRank(
        getGraderPassedValue(left.result, sort.graderName),
        sort.direction,
      );
      const rightRank = getGraderSortRank(
        getGraderPassedValue(right.result, sort.graderName),
        sort.direction,
      );

      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }

      return left.index - right.index;
    })
    .map(({ result }) => result);
}
