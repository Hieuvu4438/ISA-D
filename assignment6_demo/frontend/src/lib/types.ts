export type QueryMode = 'text' | 'voice' | 'image' | 'multimodal'
export type Category = 'running_shoes' | 'trail_shoes' | 'casual_shoes' | 'boots' | 'sandals'
  | 'bag' | 'backpack' | 'tote_bag' | 't_shirt' | 'jacket' | 'watch' | 'sunglasses'
export type VoiceSource = 'azure' | 'local' | 'groq' | 'manual_transcript'
export type ResultPolicy = 'nearest' | 'relevant'

export interface Filters {
  category?: Category | null
  brand?: string | null
  min_price?: number | null
  max_price?: number | null
  in_stock?: boolean
}

export interface SearchOptions {
  top_k: number
  result_policy: ResultPolicy
  filters: Filters
}

export interface ProductSummary {
  product_id: string
  name: string
  category: Category
  brand: string
  color: string
  price_vnd: number
  in_stock: boolean
  image_url: string
}

export interface ImageCredit {
  source_page: string
  author: string
  license: string
  license_url: string
  transformations: string[]
}

export interface ProductDetail extends ProductSummary {
  description: string
  stock_quantity: number
  image_credit: ImageCredit
}

export interface Credit extends ImageCredit {
  asset_id: string
  product_id: string
}

export interface ImageSummary {
  format: 'JPEG' | 'PNG' | 'WEBP'
  width: number
  height: number
  byte_size: number
}

export interface SearchResult {
  rank: number
  product: ProductSummary
  score: number
  component_scores: { text: number | null; image: number | null }
}

export interface SearchResponse {
  request_id: string
  query: {
    mode: QueryMode
    text: string | null
    voice_source: VoiceSource | null
    image_summary: ImageSummary | null
    text_weight: number | null
    options: SearchOptions
  }
  results: SearchResult[]
  meta: {
    model_fingerprint: string
    index_fingerprint: string
    catalog_fingerprint: string
    result_policy: ResultPolicy
    threshold: number | null
    policy_fingerprint: string | null
    empty_reason: 'catalog_empty' | 'filters' | 'threshold' | null
    timing_ms: Record<'validation' | 'encoding' | 'retrieval' | 'filtering' | 'threshold' | 'ranking' | 'hydration' | 'total', number>
    trace: { step: string; status: 'ok' | 'skipped'; input_count: number; output_count: number }[]
  }
}

export interface Capability {
  available: boolean
  reason_code: string | null
}

export interface MetaResponse {
  request_id: string
  api_version: 'v1'
  capabilities: {
    catalog: Capability
    orders: Capability
    search: Capability
    manual_transcript: Capability
    relevant: Capability & { modes: QueryMode[]; multimodal_weights: number[] }
  }
  speech: {
    provider: 'azure' | 'local' | 'groq'
    configuration_state: 'unconfigured' | 'configured_unverified'
    language: 'vi-VN'
    region: 'southeastasia' | null
    accepted_formats: string[]
    max_duration_seconds: number
    max_bytes: number
  }
  model: {
    text_model_id: string
    image_model_id: string
    text_revision: string | null
    image_revision: string | null
    dimension: 512
    model_fingerprint: string | null
  }
  index: { available: boolean; index_fingerprint: string | null; catalog_fingerprint: string | null; product_count: number }
  filters: { available: boolean; categories: Category[]; brands: string[]; min_price: number | null; max_price: number | null }
  limits: {
    text_max_characters: number
    text_max_tokens: number
    top_k_max: number
    image_max_bytes: number
    image_max_pixels: number
    image_max_dimension: number
    text_weight_min: number
    text_weight_max: number
  }
}

export interface OrderSummary {
  order_id: string
  date: string
  status: 'processing' | 'shipped' | 'delivered' | 'cancelled'
  total_vnd: number
}

export interface OrderDetail extends OrderSummary {
  items: { product_id: string; product_name: string; quantity: number; unit_price_vnd: number; line_total_vnd: number }[]
}

export interface TranscriptionResponse {
  request_id: string
  transcript: string
  language: 'vi-VN'
  provider: 'azure' | 'local' | 'groq'
  audio_duration_ms: number
  timing_ms: { validation: number; provider: number; total: number }
}

export type TextSearchRequest =
  | { mode: 'text'; text: string; options: SearchOptions }
  | { mode: 'voice'; text: string; voice_source: VoiceSource; options: SearchOptions }

export interface ProductsResponse { request_id: string; products: ProductSummary[]; total: number; offset: number; limit: number }
export interface ProductResponse { request_id: string; product: ProductDetail }
export interface CreditsResponse { request_id: string; credits: Credit[] }
export interface OrderResponse { request_id: string; order: OrderDetail }
export interface OrderSummaryResponse { request_id: string; order: OrderSummary }
export interface FieldError { field: string; message: string }
