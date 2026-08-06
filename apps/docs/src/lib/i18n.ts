import { defineI18n } from "fumadocs-core/i18n";

export const i18n = defineI18n({
  defaultLanguage: "en",
  languages: ["en", "ru", "he", "ko"],
  hideLocale: "default-locale",
  parser: "dir",
});
