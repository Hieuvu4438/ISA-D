import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';

export default defineConfig(
  { ignores: ['dist/**', 'node_modules/**'] },
  { files: ['**/*.{js,ts,tsx}'], extends: [js.configs.recommended, tseslint.configs.recommended] },
  { files: ['public/*.js'], languageOptions: { globals: {
    AudioWorkletProcessor: 'readonly', registerProcessor: 'readonly', sampleRate: 'readonly',
  } } },
);
