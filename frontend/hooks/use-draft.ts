"use client";

import * as React from "react";

/**
 * Local, editable copy of server data (form state). It is (re)initialized during render whenever `key`
 * changes (e.g. the record's updated_at), the pattern React recommends instead of syncing in an effect.
 */
export function useDraft<S, T>(source: S | undefined, key: string | undefined, init: (source: S) => T) {
  const [state, setState] = React.useState<{ key: string | undefined; value: T | null }>({ key: undefined, value: null });
  let current = state;
  if (source !== undefined && key !== undefined && state.key !== key) {
    current = { key, value: init(source) };
    setState(current);
  }
  const set = React.useCallback((value: T | ((prev: T) => T)) => {
    setState((s) => ({ ...s, value: typeof value === "function" ? (value as (prev: T) => T)(s.value as T) : value }));
  }, []);
  return [current.value, set] as const;
}
