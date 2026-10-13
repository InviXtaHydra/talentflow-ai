import { nl } from "./nl";

/** Active dictionary. Additional languages (fr, en) can be added here with the same shape as `nl`. */
const dictionaries = { nl } as const;
export type Locale = keyof typeof dictionaries;
const active: Locale = "nl";

type Params = Record<string, string | number | null | undefined>;

/** Looks up a dot-separated key ("match.components.skills") and fills {placeholders}. */
export function t(key: string, params?: Params): string {
  let node: unknown = dictionaries[active];
  for (const part of key.split(".")) {
    if (node && typeof node === "object" && part in (node as object)) node = (node as Record<string, unknown>)[part];
    else return key;
  }
  if (typeof node !== "string") return key;
  return params ? node.replace(/\{(\w+)\}/g, (_, name: string) => String(params[name] ?? "")) : node;
}

export const locale = "nl-BE";
