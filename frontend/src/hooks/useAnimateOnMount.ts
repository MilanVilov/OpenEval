import { useEffect, useState } from 'react';

/** Returns `true` after the component has mounted (with optional delay). 
 *  Use to gate CSS transition classes for entrance animations. */
export function useAnimateOnMount(delay = 0): boolean {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return visible;
}
