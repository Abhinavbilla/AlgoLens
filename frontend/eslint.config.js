import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: reactHooks.configs.recommended.rules,
  },
  {
    // Node scripts; code inside page.evaluate() runs in the browser.
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      globals: {
        process: "readonly", console: "readonly", fetch: "readonly", document: "readonly", window: "readonly",
      },
    },
  },
);
