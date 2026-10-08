import { createContext, useContext, useState, type ReactNode } from 'react';
import type { QueryMode, SearchOptions, SearchResponse, VoiceSource } from './lib/types';

export const initialOptions = (): SearchOptions => ({
  top_k: 5, result_policy: 'nearest',
  filters: { category: null, brand: null, min_price: null, max_price: null, in_stock: false },
});
export interface Draft {
  text: string;
  image: File | null;
  audio: File | null;
  weight: number;
  voiceSource: VoiceSource;
  transcriptModified: boolean;
  options: SearchOptions;
}
const freshDraft = (): Draft => ({ text: '', image: null, audio: null, weight: .5,
  voiceSource: 'manual_transcript', transcriptModified: false, options: initialOptions() });
type Drafts = Record<QueryMode, Draft>;
type Responses = Record<QueryMode, SearchResponse | null>;
interface SearchState {
  mode: QueryMode;
  setMode: (mode: QueryMode) => void;
  drafts: Drafts;
  updateDraft: (mode: QueryMode, update: Partial<Draft>) => void;
  responses: Responses;
  setResponse: (mode: QueryMode, response: SearchResponse | null) => void;
  signatures: Partial<Record<QueryMode, string>>;
  setSignature: (mode: QueryMode, value: string) => void;
  scroll: number;
  setScroll: (position: number) => void;
}
const Context = createContext<SearchState | null>(null);
export function SearchProvider({ children }: { children: ReactNode }) {
  const [mode, changeMode] = useState<QueryMode>('text');
  const [drafts, setDrafts] = useState<Drafts>({ text: freshDraft(), voice: freshDraft(), image: freshDraft(), multimodal: freshDraft() });
  const [responses, setResponses] = useState<Responses>({ text: null, voice: null, image: null, multimodal: null });
  const [scroll, setScroll] = useState(0);
  const [signatures, setSignatures] = useState<Partial<Record<QueryMode, string>>>({});
  return <Context.Provider value={{ mode, setMode: changeMode, drafts,
    updateDraft: (key, update) => setDrafts(previous => ({ ...previous, [key]: { ...previous[key], ...update } })),
    responses, setResponse: (key, response) => setResponses(previous => ({ ...previous, [key]: response })),
    signatures, setSignature: (key, value) => setSignatures(previous => ({ ...previous, [key]: value })),
    scroll, setScroll }}>{children}</Context.Provider>;
}
export function useSearchState() {
  const state = useContext(Context);
  if (!state) throw new Error('SearchProvider is required.');
  return state;
}
