import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getMeta, getProducts } from './lib/api';
import type { MetaResponse, ProductSummary } from './lib/types';

interface CatalogState { meta: MetaResponse | null; products: ProductSummary[]; loading: boolean; error: string; metaError: string; reload: () => void }
const Context = createContext<CatalogState | null>(null);
export function CatalogProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [metaError, setMetaError] = useState('');
  const [generation, setGeneration] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setMetaError('');
    void getMeta(controller.signal).then(setMeta).catch(reason => { if (!controller.signal.aborted) setMetaError(reason.message); });
    void (async () => {
      try {
        const first = await getProducts(0, 100, controller.signal);
        if (controller.signal.aborted) return;
        const all = [...first.products];
        let offset = first.products.length;
        while (offset < first.total) {
          const next = await getProducts(offset, 100, controller.signal);
          if (controller.signal.aborted) return;
          all.push(...next.products);
          offset += next.products.length;
          if (next.products.length === 0) break;
        }
        setProducts(all);
      } catch (reason: unknown) {
        if (!controller.signal.aborted) {
          const message = reason instanceof Error ? reason.message : String(reason);
          setError(message);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [generation]);
  return <Context.Provider value={{ meta, products, loading, error, metaError, reload: () => setGeneration(value => value + 1) }}>{children}</Context.Provider>;
}
export function useCatalog() { const value = useContext(Context); if (!value) throw new Error('CatalogProvider required'); return value; }
