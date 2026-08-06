import { createFromSource } from "fumadocs-core/search/server";
import { source } from "@/lib/source";

const NON_WORD = /[^\p{L}\p{N}]+/u;

function unicodeTokenizer() {
  return {
    language: "english",
    normalizationCache: new Map<string, string>(),
    tokenize(raw: string) {
      return raw.toLowerCase().split(NON_WORD).filter(Boolean);
    },
  };
}

export const { GET } = createFromSource(source, {
  localeMap: {
    en: { language: "english" },
    ru: { language: "russian" },
    he: { tokenizer: unicodeTokenizer() },
    ko: { tokenizer: unicodeTokenizer() },
  },
});
