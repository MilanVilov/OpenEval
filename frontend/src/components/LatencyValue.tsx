import { createElement, type ReactNode } from "react";

export const FLEX_LATENCY_TITLE = "because latency of flex is not reliable";

interface LatencyValueProps {
  children: ReactNode;
  unreliable: boolean;
}

/** Displays Flex-mode latency as unavailable for reliable comparison. */
export function LatencyValue({ children, unreliable }: LatencyValueProps) {
  if (!unreliable) {
    return children;
  }

  return createElement(
    "span",
    { className: "cursor-help line-through", title: FLEX_LATENCY_TITLE },
    children,
  );
}
