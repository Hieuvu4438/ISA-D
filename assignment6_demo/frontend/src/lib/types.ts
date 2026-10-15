export type QueryMode = 'text' | 'voice' | 'image' | 'multimodal'
export type Category = 'running_shoes' | 'trail_shoes' | 'casual_shoes' | 'boots' | 'sandals'
  | 'bag' | 'backpack' | 'tote_bag' | 't_shirt' | 'jacket' | 'watch' | 'sunglasses'
export type VoiceSource = 'azure' | 'local' | 'groq' | 'manual_transcript'
export type ResultPolicy = 'nearest' | 'relevant'

export interface Filters {
  category?: Category | null
  brand?: string | null
  color?: string | null
  min_price?: number | null
  max_price?: number | null
  in_stock?: boolean
}

export interface SearchOptions {
  top_k: number
  result_policy: ResultPolicy
  filters: Filters
  search_strategy?: 'semantic' | 'hybrid'
  sort?: 'relevance' | 'price_asc' | 'price_desc' | 'name'
  interpret_price?: boolean
}

export interface PriceInterpretation {
  enabled: boolean; parser_version: string; applied: boolean; lexical_text: string
  clauses: { text: string; min_price: number | null; max_price: number | null }[]
  inferred_filters: { min_price: number | null; max_price: number | null }; effective_filters: Filters
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
  rank_score?: number
  lexical_score?: number | null
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
    empty_reason: 'catalog_empty' | 'filters' | 'threshold' | 'no_matches' | null
    ranking_strategy?: 'semantic' | 'rrf' | 'exact_sku'
    sort?: string
    corrections?: { input: string; matched: string }[]
    price_interpretation?: PriceInterpretation
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
  version?: number
  subtotal_vnd?: number
  shipping_fee_vnd?: number
  payment_method?: 'cod'
  payment_status?: 'unpaid'
  demo_order?: boolean
  shipping_address?: ShippingAddress
}
export interface ShippingAddress { recipient: string; phone: string; address_line: string; city: string }
export type ReturnStatus = 'requested' | 'approved' | 'rejected' | 'withdrawn' | 'received' | 'closed'
export interface ReturnCase {
  return_id: string; order_id: string; status: ReturnStatus; version: number
  items: { product_id: string; product_name: string; quantity: number; unit_price_vnd: number }[]
  reason: string; created_at: string; updated_at: string; merchandise_value_vnd: number
  refund_status: 'not_processed' | 'demo_recorded'; refund_amount_vnd: number
  operator_note?: string; receipt?: { product_id: string; restock_quantity: number }[]
}
export interface OrderReturns {
  request_id: string; returns: ReturnCase[]; order_version: number
  eligibility: { eligible: boolean; ineligible_reason: string | null; deadline: string | null; window_days: number; policy: string
    items: (OrderDetail['items'][number] & { remaining_quantity: number })[] }
}
export interface CreateReturnRequest { version: number; idempotency_key: string; reason: string; items: { product_id: string; quantity: number }[] }
export interface CheckoutQuote { quote_id: string; cart_version: number; expires_at: number; items: OrderDetail['items']; subtotal_vnd: number; shipping_fee_vnd: number; total_vnd: number; currency: 'VND'; payment_method: 'cod' }
export interface PurchaseRequest { quote_id: string; idempotency_key: string; shipping_address: ShippingAddress }

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
export interface BrowseResponse extends ProductsResponse {
  price_interpretation?: PriceInterpretation
  query: { text: string; sort: string; filters: Filters }
  facets: Record<'category' | 'brand' | 'color', { value: string; count: number }[]>
  corrections: { input: string; matched: string }[]
  empty_reason: 'catalog_empty' | 'filters' | 'no_matches' | null
  catalog_fingerprint: string
  lexical_fingerprint: string
  retrieval: 'catalog' | 'bm25' | 'exact_sku'
}
export interface CartItem {
  product_id: string; product: ProductSummary | null; quantity: number
  unit_price_vnd: number; line_total_vnd: number; available_quantity: number
  issue: 'PRODUCT_UNAVAILABLE' | 'OUT_OF_STOCK' | 'INSUFFICIENT_STOCK' | null
}
export interface Cart {
  version: number; items: CartItem[]; item_count: number; subtotal_vnd: number
  currency: 'VND'; has_issues: boolean; stock_reserved: false
}
export interface CartResponse { request_id: string; cart: Cart }
export interface WishlistResponse { request_id: string; items: { product_id: string; product: ProductSummary | null }[]; total: number }
export interface AdminPageData {
  request_id: string; total: number; offset: number; limit: number; revision?: number
  items?: { product_id: string; quantity: number; product: ProductSummary | null }[]
  users?: { user_id: string; email: string; display_name: string; role: 'user' | 'admin'; access_state: 'active' | 'locked'; version: number }[]
  orders?: (OrderDetail & { version: number })[]
  events?: { audit_id: number; actor_id: string; action: string; subject_id: string; before: Record<string, unknown>; after: Record<string, unknown>; reason: string; created_at: string }[]
}
export interface ProductResponse { request_id: string; product: ProductDetail }
export interface CreditsResponse { request_id: string; credits: Credit[] }
export interface OrderResponse { request_id: string; order: OrderDetail }
export interface OrderSummaryResponse { request_id: string; order: OrderSummary }
export interface FieldError { field: string; message: string }
